from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📋 View Plans", callback_data="plans"),
            InlineKeyboardButton(text="👤 My Profile", callback_data="profile"),
        ],
        [
            InlineKeyboardButton(text="💬 Support", callback_data="support")
        ]
    ])


def plans_menu(plans):
    rows = []
    for plan_id, plan in plans.items():
        rows.append([
            InlineKeyboardButton(
                text=f"{plan['name']} - ₹{plan['price']} / {plan['duration_text']}",
                callback_data=f"plan:{plan_id}"
            )
        ])

    rows.append([
        InlineKeyboardButton(text="🔙 Back To Menu", callback_data="back_menu")
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_menu(plan_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Verify Payment", callback_data=f"verify:{plan_id}")],
        [InlineKeyboardButton(text="🔙 Back To Plans", callback_data="plans")]
    ])


def admin_payment_menu(user_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Approve", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton(text="❌ Reject", callback_data=f"reject:{user_id}")
        ]
    ])


def back_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Back To Menu", callback_data="back_menu")]
    ])
