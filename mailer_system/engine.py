import duckdb
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'vahdam_dtc.duckdb')
TARGETS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'targets.json')
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'campaign_log.json')


def load_targets():
    with open(TARGETS_PATH) as f:
        return json.load(f)


def _safe_query(conn, label, trigger_name, sql, zero_result):
    try:
        return conn.execute(sql).fetchall()
    except Exception as e:
        print(f"[warn] Table {label} is empty or unavailable — skipping {trigger_name} trigger")
        return zero_result


def run_queries(conn, targets):
    results = {}

    # Q1 churn_signal
    threshold = targets['churn_high_clv_threshold']
    rows = _safe_query(
        conn, 'klaviyo.profiles', 'win_back_vip',
        f"""
        SELECT
            COUNT(*) as at_risk_count,
            ROUND(SUM(predicted_clv_1y), 2) as at_risk_revenue,
            ROUND(AVG(predicted_clv_1y), 2) as avg_clv,
            ROUND(AVG(total_orders), 1) as avg_orders
        FROM klaviyo.profiles
        WHERE churn_risk IN ('high', 'winback')
        AND predicted_clv_1y > {threshold}
        """,
        [(0, 0.0, 0.0, 0.0)]
    )
    r = rows[0] if rows else (0, 0.0, 0.0, 0.0)
    results['churn_signal'] = {
        'at_risk_count': int(r[0] or 0),
        'at_risk_revenue': float(r[1] or 0),
        'avg_clv': float(r[2] or 0),
        'avg_orders': float(r[3] or 0),
    }

    # Q2 retention
    rows = _safe_query(
        conn, 'matrixify.orders', 'post_purchase_series',
        """
        WITH first_orders AS (
            SELECT customer_id,
                DATE_TRUNC('month', MIN(processed_at)) AS cohort_month,
                MIN(processed_at) AS first_date
            FROM matrixify.orders
            WHERE payment_status = 'paid' AND cancelled_at IS NULL
            GROUP BY customer_id
        ),
        second_orders AS (
            SELECT o.customer_id
            FROM matrixify.orders o
            JOIN first_orders f USING(customer_id)
            WHERE o.processed_at > f.first_date
            AND DATEDIFF('day', f.first_date, o.processed_at) <= 90
            AND o.payment_status = 'paid'
        )
        SELECT
            cohort_month,
            COUNT(f.customer_id) as cohort_size,
            COUNT(s.customer_id) as retained,
            ROUND(COUNT(s.customer_id) * 100.0 / NULLIF(COUNT(f.customer_id), 0), 1) as retention_pct
        FROM first_orders f
        LEFT JOIN second_orders s USING(customer_id)
        GROUP BY cohort_month
        ORDER BY cohort_month DESC
        LIMIT 3
        """,
        []
    )
    results['retention'] = [
        {
            'cohort_month': str(r[0]),
            'cohort_size': int(r[1] or 0),
            'retained': int(r[2] or 0),
            'retention_pct': float(r[3] or 0),
        }
        for r in rows
    ]

    # Q3 subscription_mix
    rows = _safe_query(
        conn, 'matrixify.order_line_items', 'subscription_conversion',
        """
        SELECT
            DATE_TRUNC('month', o.processed_at) as month,
            ROUND(
                SUM(CASE WHEN li.properties::TEXT ILIKE '%subscription%'
                              OR li.properties::TEXT ILIKE '%frequency%'
                         THEN li.total ELSE 0 END) * 100.0
                / NULLIF(SUM(li.total), 0), 1
            ) as subscription_pct
        FROM matrixify.order_line_items li
        JOIN matrixify.orders o USING(order_id)
        WHERE o.payment_status = 'paid'
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 3
        """,
        []
    )
    results['subscription_mix'] = [
        {'month': str(r[0]), 'subscription_pct': float(r[1] or 0)}
        for r in rows
    ]

    # Q4 cart_abandonment
    rows = _safe_query(
        conn, 'webengage.event_summary', 'cart_recovery',
        """
        SELECT
            DATE_TRUNC('week', event_date) as week,
            SUM(CASE WHEN event_name = 'Added To Cart' THEN event_count ELSE 0 END) as atc,
            SUM(CASE WHEN event_name = 'Order created' THEN event_count ELSE 0 END) as orders,
            ROUND(
                (1.0 - SUM(CASE WHEN event_name = 'Order created' THEN event_count ELSE 0 END) * 1.0
                     / NULLIF(SUM(CASE WHEN event_name = 'Added To Cart' THEN event_count ELSE 0 END), 0)
                ) * 100, 1
            ) as abandonment_pct
        FROM webengage.event_summary
        WHERE event_date >= CURRENT_DATE - INTERVAL '56 days'
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 8
        """,
        []
    )
    results['cart_abandonment'] = [
        {
            'week': str(r[0]),
            'atc': int(r[1] or 0),
            'orders': int(r[2] or 0),
            'abandonment_pct': float(r[3] or 0),
        }
        for r in rows
    ]

    # Q5 email_revenue_pct
    rows = _safe_query(
        conn, 'klaviyo.campaigns', 're_engagement',
        """
        SELECT
            DATE_TRUNC('month', k.sent_at) as month,
            ROUND(SUM(k.revenue_attributed) * 100.0 / NULLIF(MAX(r.net_sales), 0), 1) as email_pct
        FROM klaviyo.campaigns k
        JOIN shopify_analytics.revenue_metrics r
            ON DATE_TRUNC('month', k.sent_at) = r.report_date
            AND r.report_period = 'month'
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 3
        """,
        []
    )
    results['email_revenue'] = [
        {'month': str(r[0]), 'email_pct': float(r[1] or 0)}
        for r in rows
    ]

    # Q6 top_last_skus
    rows = _safe_query(
        conn, 'matrixify.order_line_items', 'win_back_vip',
        """
        SELECT li.title, COUNT(*) as purchase_count
        FROM matrixify.order_line_items li
        JOIN matrixify.orders o USING(order_id)
        JOIN klaviyo.profiles p ON o.email = p.email
        WHERE p.churn_risk IN ('high', 'winback')
        AND o.payment_status = 'paid'
        GROUP BY li.title
        ORDER BY purchase_count DESC
        LIMIT 3
        """,
        []
    )
    results['top_skus'] = [
        {'title': r[0], 'purchase_count': int(r[1] or 0)}
        for r in rows
    ]

    # Q7 winning_cta
    rows = _safe_query(
        conn, 'klaviyo.campaigns', 'all',
        """
        SELECT campaign_name, revenue_per_recipient, ctor, click_rate
        FROM klaviyo.campaigns
        WHERE channel = 'email'
        ORDER BY revenue_per_recipient DESC NULLS LAST
        LIMIT 5
        """,
        []
    )
    results['winning_cta'] = [
        {
            'campaign_name': r[0],
            'revenue_per_recipient': float(r[1] or 0),
            'ctor': float(r[2] or 0),
            'click_rate': float(r[3] or 0),
        }
        for r in rows
    ]

    return results


def evaluate_triggers(results, targets):
    triggered = []

    cs = results.get('churn_signal', {})
    retention = results.get('retention', [])
    sub_mix = results.get('subscription_mix', [])
    cart_abn = results.get('cart_abandonment', [])
    email_rev = results.get('email_revenue', [])

    # P1 win_back_vip
    if (cs.get('at_risk_revenue', 0) > targets['at_risk_revenue_trigger']
            and cs.get('avg_clv', 0) > targets['churn_high_clv_threshold']):
        triggered.append({
            'campaign_type': 'win_back_vip',
            'priority': 1,
            'trigger_reason': (
                f"At-risk revenue ${cs['at_risk_revenue']:,.0f} exceeds "
                f"${targets['at_risk_revenue_trigger']:,.0f} threshold; "
                f"avg CLV ${cs['avg_clv']:.0f} exceeds ${targets['churn_high_clv_threshold']:.0f}"
            ),
            'context_data': results,
        })

    # P2 post_purchase_series
    below_retention = sum(
        1 for r in retention
        if r['retention_pct'] < targets['retention_90d_min'] * 100
    )
    if below_retention >= 2:
        triggered.append({
            'campaign_type': 'post_purchase_series',
            'priority': 2,
            'trigger_reason': (
                f"90-day retention below {targets['retention_90d_min']*100:.0f}% target "
                f"in {below_retention}/3 recent cohorts"
            ),
            'context_data': results,
        })

    # P3 subscription_conversion
    below_sub = sum(
        1 for r in sub_mix
        if r['subscription_pct'] < targets['subscription_mix_min'] * 100
    )
    if below_sub >= 2:
        triggered.append({
            'campaign_type': 'subscription_conversion',
            'priority': 3,
            'trigger_reason': (
                f"Subscription mix below {targets['subscription_mix_min']*100:.0f}% target "
                f"in {below_sub}/3 recent months"
            ),
            'context_data': results,
        })

    # P4 cart_recovery
    if cart_abn:
        latest_abn = cart_abn[0]['abandonment_pct']
        if latest_abn > targets['cart_abandonment_max'] * 100:
            triggered.append({
                'campaign_type': 'cart_recovery',
                'priority': 4,
                'trigger_reason': (
                    f"Cart abandonment {latest_abn:.1f}% exceeds "
                    f"{targets['cart_abandonment_max']*100:.0f}% max threshold this week"
                ),
                'context_data': results,
            })

    # P5 re_engagement
    below_email_rev = sum(
        1 for r in email_rev
        if r['email_pct'] < targets['email_revenue_pct_min'] * 100
    )
    if below_email_rev >= 2:
        triggered.append({
            'campaign_type': 're_engagement',
            'priority': 5,
            'trigger_reason': (
                f"Email revenue contribution below {targets['email_revenue_pct_min']*100:.0f}% target "
                f"in {below_email_rev}/3 recent months"
            ),
            'context_data': results,
        })

    # P6 geo_upsell — monthly fallback if nothing else fires
    if not triggered:
        triggered.append({
            'campaign_type': 'geo_upsell',
            'priority': 6,
            'trigger_reason': 'Monthly geo-upsell fallback - all metrics within targets',
            'context_data': results,
        })

    return triggered


def log_to_campaign_log(entry):
    entry['timestamp'] = datetime.now().isoformat()
    with open(LOG_PATH, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def get_triggered_campaigns():
    targets = load_targets()

    try:
        conn = duckdb.connect(DB_PATH, read_only=True)
    except Exception as e:
        print(f"[warn] Cannot connect to {DB_PATH}: {e}")
        fallback = [{
            'campaign_type': 'geo_upsell',
            'priority': 6,
            'trigger_reason': 'Database unavailable — geo_upsell fallback',
            'context_data': {},
        }]
        log_to_campaign_log({'metrics': {}, 'triggered': ['geo_upsell'], 'note': str(e)})
        return fallback

    try:
        results = run_queries(conn, targets)
        triggered = evaluate_triggers(results, targets)
        log_to_campaign_log({
            'metrics': results,
            'triggered': [t['campaign_type'] for t in triggered],
        })
        return triggered
    finally:
        conn.close()


def print_metric_report(results, targets):
    cs = results.get('churn_signal', {})
    retention = results.get('retention', [])
    sub_mix = results.get('subscription_mix', [])
    cart_abn = results.get('cart_abandonment', [])
    email_rev = results.get('email_revenue', [])

    print("\n-- Metric Readings ------------------------------------------")
    print(f"  Churn signal       : {cs.get('at_risk_count', 0)} at-risk customers")
    print(f"  At-risk revenue    : ${cs.get('at_risk_revenue', 0):,.0f}  (trigger > ${targets['at_risk_revenue_trigger']:,.0f})")
    print(f"  Avg CLV at-risk    : ${cs.get('avg_clv', 0):.0f}  (threshold > ${targets['churn_high_clv_threshold']:.0f})")

    if retention:
        for r in retention:
            flag = "BELOW" if r['retention_pct'] < targets['retention_90d_min'] * 100 else "ok"
            print(f"  Retention {r['cohort_month'][:7]} : {r['retention_pct']:.1f}%  (target >= {targets['retention_90d_min']*100:.0f}%) [{flag}]")
    else:
        print("  Retention          : no data")

    if sub_mix:
        for r in sub_mix:
            flag = "BELOW" if r['subscription_pct'] < targets['subscription_mix_min'] * 100 else "ok"
            print(f"  Sub mix {r['month'][:7]}    : {r['subscription_pct']:.1f}%  (target >= {targets['subscription_mix_min']*100:.0f}%) [{flag}]")
    else:
        print("  Subscription mix   : no data")

    if cart_abn:
        r = cart_abn[0]
        flag = "ABOVE" if r['abandonment_pct'] > targets['cart_abandonment_max'] * 100 else "ok"
        print(f"  Cart abandonment   : {r['abandonment_pct']:.1f}%  (max {targets['cart_abandonment_max']*100:.0f}%) [{flag}]")
    else:
        print("  Cart abandonment   : no data")

    if email_rev:
        for r in email_rev:
            flag = "BELOW" if r['email_pct'] < targets['email_revenue_pct_min'] * 100 else "ok"
            print(f"  Email rev% {r['month'][:7]} : {r['email_pct']:.1f}%  (target >= {targets['email_revenue_pct_min']*100:.0f}%) [{flag}]")
    else:
        print("  Email revenue %    : no data")

    print("-------------------------------------------------------------\n")
