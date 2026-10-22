import streamlit as st
import sqlite3
from datetime import date

st.set_page_config(page_title="MoneyMind", page_icon="💰", layout="wide")

# --- DATABASE SETUP ---
conn = sqlite3.connect("moneymind.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute(
    """CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT
    )"""
)

cursor.execute(
    """CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        expense_date TEXT,
        item TEXT,
        category TEXT,
        amount REAL
    )"""
)
conn.commit()

# --- USER SESSION ---
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None

# --- AUTHENTICATION ---
if st.session_state.user_id is None:
    st.title("💰 MoneyMind")
    st.subheader("Login or Register")

    auth_choice = st.radio("Select Action:", ["Login", "Sign Up"])

    if auth_choice == "Sign Up":
        new_user = st.text_input("New Username:")
        new_pass = st.text_input("New Password:", type="password")
        if st.button("Create Account"):
            if new_user and new_pass:
                try:
                    cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (new_user, new_pass))
                    conn.commit()
                    st.success("Account created successfully! Now switch to Login.")
                except:
                    st.error("Username already taken! Try another.")
            else:
                st.warning("Please fill both username and password.")

    elif auth_choice == "Login":
        user_name = st.text_input("Username:")
        user_pass = st.text_input("Password:", type="password")
        if st.button("Login"):
            cursor.execute("SELECT id, username FROM users WHERE username = ? AND password = ?", (user_name, user_pass))
            account = cursor.fetchone()
            if account:
                st.session_state.user_id = account[0]
                st.session_state.username = account[1]
                st.rerun()
            else:
                st.error("Wrong Username or Password.")

# --- DASHBOARD (LOGGED IN) ---
else:
    top_col1, top_col2 = st.columns([4, 1])
    with top_col1:
        st.title("💰 MoneyMind")
        st.write(f"Logged in as: **{st.session_state.username}**")
    with top_col2:
        st.write("")
        if st.button("🚪 Logout"):
            st.session_state.user_id = None
            st.session_state.username = None
            st.rerun()

    tab1, tab2, tab3 = st.tabs(["📅 Daily Expense & View", "📊 Overall Dashboard", "🎯 Budget & Runway"])

    # ==================== TAB 1: DAILY VIEW ====================
    with tab1:
        st.header("Daily Expense Management")
        
        # 1. Date Selection
        selected_date = st.date_input("Select Date to View / Add Expenses:", value=date.today())
        date_str = str(selected_date)

        st.divider()

        # 2. Add Expense Form for Selected Date
        st.subheader(f"Add Expense for {date_str}")
        with st.form("daily_form", clear_on_submit=True):
            col_a, col_b = st.columns(2)
            with col_a:
                cat = st.selectbox("Category:", ["Food", "Travel / Transport", "Tea & Snacks", "College & Books", "Entertainment", "Others"])
            with col_b:
                amt = st.number_input("Amount (₹):", min_value=0.0, step=10.0)
            item = st.text_input("Item Description (e.g. Lunch, Bus ticket, Xerox):")
            
            btn_save = st.form_submit_button("💾 Save Expense")

            if btn_save:
                if amt > 0:
                    cursor.execute(
                        "INSERT INTO expenses (user_id, expense_date, item, category, amount) VALUES (?, ?, ?, ?, ?)",
                        (st.session_state.user_id, date_str, item, cat, amt)
                    )
                    conn.commit()
                    st.success(f"Saved ₹{amt:,.2f} for '{item or cat}' on {date_str}!")
                    st.rerun()
                else:
                    st.warning("Please enter an amount greater than 0.")

        # 3. View Expenses ONLY for Selected Date
        cursor.execute(
            "SELECT id, category, item, amount FROM expenses WHERE user_id = ? AND expense_date = ? ORDER BY id DESC",
            (st.session_state.user_id, date_str)
        )
        day_records = cursor.fetchall()

        st.divider()
        if day_records:
            day_total = sum(r[3] for r in day_records)
            st.metric(label=f"Total Expense for {date_str}", value=f"₹{day_total:,.2f}")
            
            st.subheader(f"Expenses on {date_str}:")
            for idx, r in enumerate(day_records, 1):
                st.write(f"{idx}. **{r[1]}** | {r[2]} : **₹{r[3]:,.2f}**")
        else:
            st.info(f"No expenses recorded for {date_str}. Add an entry above!")

    # ==================== TAB 2: OVERALL DASHBOARD ====================
    with tab2:
        st.header("Overall Spending Dashboard")
        
        # All time records for this user
        cursor.execute(
            "SELECT expense_date, category, item, amount FROM expenses WHERE user_id = ? ORDER BY expense_date DESC",
            (st.session_state.user_id,)
        )
        all_records = cursor.fetchall()

        if all_records:
            grand_total = sum(r[3] for r in all_records)
            st.metric(label="All-Time Total Expense", value=f"₹{grand_total:,.2f}")
            st.divider()

            # Date-wise breakdown
            st.subheader("🗓️ Date-wise Total Spending:")
            cursor.execute(
                """SELECT expense_date, SUM(amount), COUNT(id) 
                   FROM expenses 
                   WHERE user_id = ? 
                   GROUP BY expense_date 
                   ORDER BY expense_date DESC""",
                (st.session_state.user_id,)
            )
            date_summary = cursor.fetchall()
            for ds in date_summary:
                st.write(f"📅 **{ds[0]}** : Total **₹{ds[1]:,.2f}** ({ds[2]} items)")

            st.divider()

            # Category-wise breakdown
            st.subheader("🏷️ Category-wise Spending:")
            cursor.execute(
                """SELECT category, SUM(amount) 
                   FROM expenses 
                   WHERE user_id = ? 
                   GROUP BY category 
                   ORDER BY SUM(amount) DESC""",
                (st.session_state.user_id,)
            )
            cat_summary = cursor.fetchall()
            for cs in cat_summary:
                st.write(f"• **{cs[0]}** : ₹{cs[1]:,.2f}")
        else:
            st.info("No expense data available yet to show in the dashboard.")

    # ==================== TAB 3: BUDGET RUNWAY ====================
    with tab3:
        st.header("Monthly Pocket Money & Runway Tracker")
        pm = st.number_input("Monthly Pocket Money (₹):", min_value=0.0, step=500.0, key="pm_tab3")
        
        # Calculate all-time spent
        cursor.execute("SELECT SUM(amount) FROM expenses WHERE user_id = ?", (st.session_state.user_id,))
        total_db_spent = cursor.fetchone()[0] or 0.0
        
        st.write(f"Total Amount Spent from Records: **₹{total_db_spent:,.2f}**")
        daily_est = st.number_input("Estimated Daily Spending (₹):", min_value=0.0, step=50.0, key="daily_tab3")

        if st.button("Calculate Balance & Runway"):
            bal = pm - total_db_spent
            st.subheader(f"Remaining Balance: ₹{bal:,.2f}")

            if daily_est > 0 and bal > 0:
                days = bal / daily_est
                st.info(f"Your balance may last around **{days:.1f} days**.")
            elif bal <= 0 and pm > 0:
                st.error("🚨 Warning: Pocket money is fully exhausted!")