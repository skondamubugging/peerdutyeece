import pandas as pd
import random
import streamlit as st
import logging

# Suppress Streamlit warnings
logging.getLogger("streamlit").setLevel(logging.ERROR)

# -----------------------------------
# Function to generate peer assignments
# -----------------------------------
def generate_peer_assignments(input_file):
    # List of weekday sheets
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

    # Read all sheets
    all_sheets = pd.read_excel(input_file, sheet_name=days)
    summary_rows = []

    for day in days:
        df = all_sheets[day]
        df.columns = df.columns.str.strip()

        if "Sl. No." in df.columns:
            df = df.drop(columns=["Sl. No."])

        faculty_cols = ["Name of the Faculty", "Designation", "Emp ID"]
        time_slots = [col for col in df.columns if col not in faculty_cols]

        # Remove 08:00 - 08:50 slot
        time_slots = [ts for ts in time_slots if not ts.startswith("08:00")]

        df_long = df.melt(
            id_vars=faculty_cols,
            value_vars=time_slots,
            var_name="Time Slot",
            value_name="Assigned Work"
        )
        df_long["Day"] = day
        df_long["Status"] = df_long["Assigned Work"].apply(
            lambda x: "Busy" if pd.notna(x) and str(x).strip() != "" else "Free"
        )
        df_long = df_long.rename(columns={"Name of the Faculty": "Faculty Name"})
        summary_rows.append(df_long)

    # Combine all days
    summary = pd.concat(summary_rows, ignore_index=True)
    summary = summary[
        ["Day", "Time Slot", "Faculty Name", "Designation", "Emp ID", "Status", "Assigned Work"]
    ]

    # -----------------------------------
    # Peer assignment (one class per slot, skipping 8am)
    # -----------------------------------
    peer_assignments = []
    assigned_faculty = set()
    time_slot_order = sorted(summary["Time Slot"].unique())

    def is_available_before_after(faculty, day, slot):
        idx = time_slot_order.index(slot)
        prev_slot = time_slot_order[idx - 1] if idx > 0 else None
        next_slot = time_slot_order[idx + 1] if idx < len(time_slot_order) - 1 else None

        if prev_slot is not None:
            prev_status = summary[
                (summary["Day"] == day) &
                (summary["Time Slot"] == prev_slot) &
                (summary["Faculty Name"] == faculty)
            ]["Status"].values[0]
            if prev_status != "Free":
                return False
        if next_slot is not None:
            next_status = summary[
                (summary["Day"] == day) &
                (summary["Time Slot"] == next_slot) &
                (summary["Faculty Name"] == faculty)
            ]["Status"].values[0]
            if next_status != "Free":
                return False
        return True

    for (day, slot), group in summary.groupby(["Day", "Time Slot"]):
        busy_classes = group[group["Status"] == "Busy"]
        free_faculty = group[group["Status"] == "Free"]["Faculty Name"].unique().tolist()

        # Filter only faculty free before AND after
        free_faculty = [f for f in free_faculty if is_available_before_after(f, day, slot)]

        if busy_classes.empty or len(free_faculty) == 0:
            peer_assignments.append({
                "Day": day,
                "Time Slot": slot,
                "Busy Faculty": "None",
                "Class": "No Class",
                "Peer Faculty": "None",
                "Alternative Faculty": "None"
            })
            continue

        chosen_class = busy_classes.sample(1).iloc[0]

        available = [f for f in free_faculty if f not in assigned_faculty and f != "Prof. P. Bharani Chandra Kumar","Dr. K. Srichandan"]
        if not available:
            assigned_faculty.clear()
            available = free_faculty

        peer = random.choice(available)
        assigned_faculty.add(peer)

        # Pick 3 randomized alternatives
        alt_faculty = [f for f in free_faculty if f != peer and f != "Prof. P. Bharani Chandra Kumar","Dr. K. Srichandan"]
        random.shuffle(alt_faculty)
        alt_faculty = alt_faculty[:3]

        peer_assignments.append({
            "Day": day,
            "Time Slot": slot,
            "Busy Faculty": chosen_class["Faculty Name"],
            "Class": chosen_class["Assigned Work"],
            "Peer Faculty": peer,
            "Alternative Faculty": ", ".join(alt_faculty) or "None"
        })

    peer_df = pd.DataFrame(peer_assignments)
    return peer_df

# -----------------------------------
# Streamlit Dashboard
# -----------------------------------
def main():
    st.set_page_config(page_title="Peer Assignment Dashboard", layout="wide")
    st.title("🧑‍🏫 Faculty Peer Assignment Dashboard")

    # Fixed Excel file path (no upload)
    excel_file = "Peercopy.xlsx"
    peer_df = generate_peer_assignments(excel_file)

    # Sidebar filters
    st.sidebar.header("Filters")
    day_filter = st.sidebar.multiselect(
        "Select Day(s)",
        options=peer_df["Day"].unique(),
        default=peer_df["Day"].unique()
    )
    faculty_filter = st.sidebar.multiselect(
        "Select Faculty",
        options=peer_df["Peer Faculty"].unique(),
        default=peer_df["Peer Faculty"].unique()
    )
    class_filter = st.sidebar.multiselect(
        "Select Class/Subject",
        options=peer_df["Class"].unique(),
        default=peer_df["Class"].unique()
    )

    # Apply filters
    filtered_df = peer_df[
        (peer_df["Day"].isin(day_filter)) &
        (peer_df["Peer Faculty"].isin(faculty_filter)) &
        (peer_df["Class"].isin(class_filter))
    ]

    # Display results
    st.subheader("📋 Detailed Peer Assignments")
    st.dataframe(filtered_df[
        ["Day", "Time Slot", "Busy Faculty", "Class", "Peer Faculty", "Alternative Faculty"]
    ])

if __name__ == "__main__":
    main()
