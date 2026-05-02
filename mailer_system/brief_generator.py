import json
import os
from datetime import datetime


def get_seasonal_hook():
    month = datetime.now().month
    hooks = {
        1: "New Year ritual reset",
        2: "Valentine gifting",
        3: "Spring wellness reset",
        4: "Spring wellness reset",
        5: "Mother's Day",
        6: None,
        7: None,
        8: None,
        9: "Autumn harvest season",
        10: "Diwali gifting",
        11: "Holiday gifting season",
        12: "Holiday gifting season",
    }
    return hooks.get(month)


def get_offer(avg_clv):
    if avg_clv > 200:
        return "15% off"
    elif avg_clv >= 50:
        return "Free shipping on your next order"
    return None


def extract_winning_cta_word(winning_cta_rows):
    if not winning_cta_rows:
        return "Discover"
    verbs = ["Discover", "Shop", "Explore", "Try", "Find", "Get", "Restore", "Begin", "Steep"]
    name_text = " ".join(r['campaign_name'] for r in winning_cta_rows if r.get('campaign_name'))
    for verb in verbs:
        if verb.lower() in name_text.lower():
            return verb
    return "Discover"


def get_last_open_rate(conn):
    try:
        row = conn.execute("""
            SELECT open_rate FROM klaviyo.campaigns
            WHERE channel = 'email' AND open_rate IS NOT NULL
            ORDER BY sent_at DESC LIMIT 1
        """).fetchone()
        return float(row[0]) if row else None
    except Exception:
        return None


def build_brief(campaign, conn=None):
    ctx = campaign.get('context_data', {})
    cs = ctx.get('churn_signal', {})
    retention = ctx.get('retention', [])
    sub_mix = ctx.get('subscription_mix', [])
    top_skus = ctx.get('top_skus', [])
    winning_cta = ctx.get('winning_cta', [])

    avg_clv = cs.get('avg_clv', 0)
    at_risk_count = cs.get('at_risk_count', 0)
    at_risk_revenue = cs.get('at_risk_revenue', 0)

    product = (top_skus[0]['title'] if top_skus else "Darjeeling First Flush")
    campaign_type = campaign.get('campaign_type', 'geo_upsell')

    audience_map = {
        'win_back_vip': f"High-CLV lapsed customers at risk of churning (avg CLV ${avg_clv:.0f})",
        'post_purchase_series': "Recent first-time buyers within 90-day retention window",
        'subscription_conversion': "Active one-time buyers not yet on subscription",
        'cart_recovery': "Shoppers who added to cart but did not complete purchase",
        're_engagement': "Subscribed email list — low recent engagement segment",
        'geo_upsell': "US and UK active customer base — geo-targeted upsell audience",
    }

    retention_pct_current = retention[0]['retention_pct'] if retention else 0

    targets_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'targets.json')
    with open(targets_path) as f:
        targets = json.load(f)

    sub_pct_current = sub_mix[0]['subscription_pct'] if sub_mix else 0
    winning_cta_word = extract_winning_cta_word(winning_cta)

    last_open_rate = None
    if conn:
        last_open_rate = get_last_open_rate(conn)

    brief = {
        "product": product,
        "goal": campaign_type,
        "audience_description": audience_map.get(campaign_type, "Vahdam email subscribers"),
        "audience_size": at_risk_count if campaign_type == 'win_back_vip' else 0,
        "offer": get_offer(avg_clv),
        "seasonal_hook": get_seasonal_hook(),
        "feedback": {
            "last_open_rate": last_open_rate,
            "winning_cta_word": winning_cta_word,
            "best_send_day": "Tuesday",
        },
        "real_numbers": {
            "at_risk_revenue": at_risk_revenue,
            "segment_size": at_risk_count,
            "days_since_order_avg": 74,
            "retention_rate_current": retention_pct_current,
            "retention_rate_target": targets['retention_90d_min'] * 100,
            "subscription_pct_current": sub_pct_current,
            "top_skus": [s['title'] for s in top_skus],
            "winning_cta": winning_cta[0] if winning_cta else {},
        },
    }

    return brief
