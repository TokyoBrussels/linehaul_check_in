import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime
import pytz
import plotly.express as px

timezone = pytz.timezone('Asia/Bangkok')

st.set_page_config(
    layout="wide",
    page_title="TPK PMO Integrations", 
    page_icon="https://veldent.co.th/wp-content/uploads/2023/07/lazada-laz-square-app-icon-png-11662642316spbjkos15u-e1690258503701.png"  # Replace with your icon URL
)

st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://static.vecteezy.com/system/resources/previews/007/278/150/non_2x/dark-background-abstract-with-light-effect-vector.jpg");
        background-size: cover;
    }
    </style>
    """,
    unsafe_allow_html=True
)

logging.basicConfig(
    filename="app.log",
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

logging.debug("App started.")

creds = st.secrets["google_credentials"]
SCOPE = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(creds, scopes=SCOPE)
gc = gspread.authorize(credentials)

SHEET_ID = "1i960p5r3HH72nD0r23eo5BFzNbbG-5EQ2BOdzAaL4rw"

USER_WORKSHEET_NAME = "AppUser"
user_sheet = gc.open_by_key(SHEET_ID).worksheet(USER_WORKSHEET_NAME)
user_data = user_sheet.get_all_records()
user_df = pd.DataFrame(user_data)

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'queue' not in st.session_state:
    st.session_state.queue = ""
if 'truck_info' not in st.session_state:
    st.session_state.truck_info = None

if not st.session_state.logged_in:
    st.title("USER LOG IN")
    user_id = st.text_input("Enter WFM ID to log in:")

    if st.button("Log In"):
        if user_id in user_df['user_id'].astype(str).values: 
            st.success(f"Welcome, User {user_id}!")
            logging.info(f"User {user_id} successfully logged in.")
            st.session_state.logged_in = True  
            st.session_state.user_id = user_id
        else:
            st.error("User ID not found. Please check and try again.")
            logging.warning(f"Log-in attempt failed for User ID: {user_id}")
else:

    MAIN_WORKSHEET_NAME = "AppData"
    main_sheet = gc.open_by_key(SHEET_ID).worksheet(MAIN_WORKSHEET_NAME)
    main_data = main_sheet.get_all_records()
    df = pd.DataFrame(main_data)

    st.title("LHS CHECK-IN APPLICATION")

    tabs = st.tabs(["🟢 CHECK-IN", "🟢 REPLACEMENT", "🟢 REPORT", "🟢 LOADING"])

    def fetch_truck_info(check_in_queue):
        if check_in_queue.isdigit():  # Ensure the input is a valid number
            matching_trucks = df[df['check_in_queue'] == int(check_in_queue)]
            if not matching_trucks.empty:  # Explicitly check if the DataFrame is not empty
                truck_info = matching_trucks.iloc[0]  # Get the first matching truck
                return truck_info
        return None

    with tabs[0]:
            st.header("CHECK-IN")

            truck_id = st.text_input("Enter Truck ID:")

            if truck_id:
                logging.debug(f"Truck ID entered: {truck_id}")
                truck_data = df[df['truck_id'] == truck_id]

                if not truck_data.empty:
                    logging.info(f"Truck data found: {truck_id}")
                    no_status_data = truck_data[truck_data['status'].isna() | (truck_data['status'] == '')]
                    has_status_data = truck_data[truck_data['status'].notna() & (truck_data['status'] != '')]

                    if not no_status_data.empty:
                        selected_truck = no_status_data.iloc[0]
                    else:
                        selected_truck = has_status_data.iloc[0]

                    st.write("Truck Details:")

                    truck_info = {
                        "Origin Node": selected_truck['origin_node'],
                        "Vendor": selected_truck['vendor_name'],
                        "Driver": selected_truck['driver_name'],
                        "Driver Contact": selected_truck['driver_tel'],
                        "Truck Type": selected_truck['vehicle_type'],
                        "Status": selected_truck['status'],
                        "Estimated Time Of Arrival": selected_truck['eta_ts'],
                        "Check-In Time": selected_truck['check_in_ts'],
                    }

                    df_truck_info = pd.DataFrame(truck_info.items(), columns=['Detail', 'Value'])
                    st.table(df_truck_info)

                    current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

                    if st.button("Check-in"):
                        logging.debug("Check-in button pressed.")
                        row_to_update = truck_data[truck_data['truck_id'] == selected_truck['truck_id']].index[0]
                        
                        if row_to_update is not None:
                            current_status = selected_truck['status']
                            if pd.notna(current_status) and current_status != '':
                                st.warning(f"Check-in blocked: Truck {truck_id} already has a status: '{current_status}'.")
                                logging.warning(f"Check-in blocked for truck {truck_id} with existing status: '{current_status}'")
                            else:
                                user_id = st.session_state.user_id
                                current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")
                                eta_time = pd.to_datetime(selected_truck['eta_ts'])
                                current_time_obj = pd.to_datetime(current_time)

                                time_difference = (eta_time - current_time_obj).total_seconds() / 3600

                                if current_time_obj > eta_time:
                                    status = "late_check_in"
                                elif current_time_obj < eta_time and time_difference < 2:
                                    status = "onTime_check_in"
                                else:
                                    status = "early_check_in"

                                check_in_history_global = df[df['check_in_ts'].notna() & (df['check_in_ts'] != '')]
                                check_in_queue = len(check_in_history_global) + 1  # Increment based on global check-ins

                                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('check_in_ts') + 1, current_time)
                                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('status') + 1, status)
                                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('update_by') + 1, user_id)
                                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('check_in_queue') + 1, check_in_queue)

                                st.success(f"Check-in time recorded: {current_time}, Status updated to '{status}', Check-in queue position: {check_in_queue}.")
                                logging.info(f"Check-in time, status, and queue updated for {truck_id}: {current_time}, '{status}', Queue: {check_in_queue}")

                                main_data = main_sheet.get_all_records()
                                df = pd.DataFrame(main_data)

                                selected_truck = df.loc[row_to_update]

                                truck_info = {
                                    "Origin Node": selected_truck['origin_node'],
                                    "Vendor": selected_truck['vendor_name'],
                                    "Driver": selected_truck['driver_name'],
                                    "Driver Contact": selected_truck['driver_tel'],
                                    "Truck Type": selected_truck['vehicle_type'],
                                    "Status": selected_truck['status'],
                                    "Estimated Time Of Arrival": selected_truck['eta_ts'],
                                    "Check-In Time": selected_truck['check_in_ts'],
                                }

                                df_truck_info = pd.DataFrame(truck_info.items(), columns=['Detail', 'Value'])
                                st.table(df_truck_info)
                    
                        else:
                            st.warning(f"Truck ID {truck_id} not found.")
                            logging.warning(f"Truck ID {truck_id} not found in data.")

    with tabs[1]:
        st.header("REPLACEMENT")
        
        with st.form("replace_form"):
            replace_truck_id = st.text_input("Replacement Truck ID:")
            new_truck_id = st.text_input("New Truck ID:")
            origin_node = st.selectbox("Origin Node Name:", ["TPK-SSW","TPK", "SSW"])
            vendor_name = st.selectbox("Vendor:", ["PJT", "TTA", "WML", "SPT", "TPS", "TKQ", "PRM", "TRN", "NES", "SWL", "TAE", "PCT", "SRY", "KJT"])
            driver_name = st.text_input("Driver Name:")
            driver_tel = st.text_input("Driver Tel:")
            vehicle_type = st.selectbox("Vehicle Type:", ["4W5CBM", "4W10CBM", "4W12CBM", "4W13CBM"])
            
            submit_button = st.form_submit_button("Confirm Replace")
            
            if submit_button:
                logging.debug(f"Submit button pressed for replace, checking replacement truck ID: {replace_truck_id}")
                current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")
                logging.debug(f"Current time: {current_time}")
                    
                if replace_truck_id in df['truck_id'].values:
                    truck_data = df[df['truck_id'] == replace_truck_id]
                    current_status = truck_data.iloc[0]['status']

                    if pd.notna(current_status) and current_status != '':
                        st.warning(f"Replacement truck {replace_truck_id} already has status: '{current_status}'. Replacement blocked.")
                        logging.warning(f"Replacement blocked for {replace_truck_id} as status is already set: '{current_status}'")
                    else:
                        user_id = st.session_state.user_id

                        check_in_history_global = df[df['check_in_ts'].notna() & (df['check_in_ts'] != '')]
                        check_in_queue = len(check_in_history_global) + 1
                        
                        new_row = [ 
                            current_time,
                            origin_node,
                            vendor_name,
                            new_truck_id,
                            driver_name,
                            driver_tel,
                            vehicle_type,
                            'replace_check_in',
                            current_time,
                            replace_truck_id,
                            user_id,
                            check_in_queue
                        ]
                            
                        try:
                            main_sheet.append_row(new_row)
                            row_A = df[df['truck_id'] == replace_truck_id].index         
                            if not row_A.empty:
                                main_sheet.update_cell(row_A[0] + 2, df.columns.get_loc('status') + 1, f"replace_by_{new_truck_id}")
            
                                st.success(f"New truck {new_truck_id} successfully logged as a replacement for {replace_truck_id}. Status updated to 'replace_by_{new_truck_id}', updated by {user_id}. Queue number: {check_in_queue}.")
                                logging.info(f"New truck {new_truck_id} logged for replacement of {replace_truck_id}, status updated to 'replace_by_{new_truck_id}', queue number: {check_in_queue}, updated by {user_id}.") 
                                    
                        except Exception as e:
                            st.error(f"Failed to log new truck: {e}")
                            logging.error(f"Failed to log new truck for {replace_truck_id}: {e}")
                else:
                    st.error("Replacement Truck ID not found in records.")

    with tabs[2]:
        st.header("Real-Time Dashboard")
        st.subheader("Check-in Status Distribution")

        df['status'] = df['status'].replace({None: 'pending', pd.NA: 'pending', '': 'pending'}).fillna('pending')
        df['status'] = df['status'].replace(r'^replace_by_.*', 'canceled_replaced', regex=True)
        status_counts = df['status'].value_counts()

        fig_pie = px.pie(
            names=status_counts.index,
            values=status_counts.values,    
            title="Check-in Status Distribution"
        )

        st.plotly_chart(fig_pie)

        st.subheader("ETA vs Check-in Time Comparison")

        df['eta_ts'] = pd.to_datetime(df['eta_ts'])
        df['check_in_ts'] = pd.to_datetime(df['check_in_ts'], errors='coerce')

        df['eta_hour'] = df['eta_ts'].dt.floor('H')
        df['check_in_hour'] = df['check_in_ts'].dt.floor('H')

        eta_hourly_count = df.groupby('eta_hour')['eta_ts'].count().reset_index(name='Plan')
        checkin_hourly_count = df.groupby('check_in_hour')['check_in_ts'].count().reset_index(name='Actual')

        eta_hourly_count.rename(columns={'eta_hour': 'hour'}, inplace=True)
        checkin_hourly_count.rename(columns={'check_in_hour': 'hour'}, inplace=True)

        hourly_comparison = pd.merge(eta_hourly_count, checkin_hourly_count, on='hour', how='outer').fillna(0)

        fig_column = px.bar(
            hourly_comparison,
            x='hour',
            y=['Plan', 'Actual'],
            labels={'value': 'Count', 'hour': 'Time'},
            title="ETA vs. Check-in Time Comparison"
        )

        st.plotly_chart(fig_column)

    with tabs[3]:
        st.header("Loading Assignment")

        checked_in_trucks = df[df['check_in_ts'].notna()].sort_values(by="check_in_queue")

        if not checked_in_trucks.empty:
            st.dataframe(checked_in_trucks[['check_in_ts', 'origin_node', 'check_in_queue', 'truck_id', 'driver_name', 'driver_tel', 'vendor_name', 'vehicle_type', 'status', 'assign_bay', 'destination_1', 'destination_2', 'exceptional']])

        check_in_queue = st.text_input("Queue", key="queue_input")

        if check_in_queue and check_in_queue != st.session_state.queue:
            truck_info = fetch_truck_info(check_in_queue)
            if truck_info is not None and not truck_info.empty:
                st.session_state.truck_info = truck_info 
                st.session_state.queue = check_in_queue 
            else:
                st.warning(f"No truck found for queue: {check_in_queue}")
                st.session_state.truck_info = None  

        truck_info = st.session_state.truck_info

        if truck_info is not None and not truck_info.empty:
            truck_id = truck_info['truck_id']
            driver_name = truck_info['driver_name']
            vehicle_type = truck_info['vehicle_type']
            driver_tel = truck_info['driver_tel']
            row_to_update = truck_info.name
        else:
            truck_id = driver_name = vehicle_type = driver_tel = row_to_update = None  
        
        with st.form(key='assignment_form'):
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.text_input("Truck ID", truck_id if truck_id else "", disabled=True)
            with col2:
                st.text_input("Driver Name", driver_name if driver_name else "", disabled=True)
            with col3:
                st.text_input("Driver Tel", driver_tel if driver_tel else "", disabled=True)
            with col4:
                st.text_input("Truck Type", vehicle_type if vehicle_type else "",disabled=True)

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                assign_bay = st.text_input("Assign Bay", "")
            with col2:
                destination_1 = st.text_input("Destination 1", "")
            with col3:
                destination_2 = st.text_input("Destination 2", "")
            with col4:
                exceptional = st.text_input("Reason/Remark", "")   

            submit_button = st.form_submit_button(label="Confirm")

        if submit_button and row_to_update is not None: 
            assign_bay_ts = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
            assign_bay_by = st.session_state['user_id'] 
            try:
                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('assign_bay') + 1, assign_bay)
                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('destination_1') + 1, destination_1)
                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('destination_2') + 1, destination_2)
                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('exceptional') + 1, exceptional)
                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('assign_bay_ts') + 1, assign_bay_ts)
                main_sheet.update_cell(row_to_update + 2, df.columns.get_loc('assign_bay_by') + 1, assign_bay_by)

                st.success(f"Truck {truck_id} successfully updated!")

            except Exception as e:
                st.error(f"Failed to update Google Sheet: {e}")
                logging.error(f"Error updating Google Sheet for Truck {truck_id}: {e}")
        elif submit_button:
            st.warning("Truck not found or queue number invalid. Please check the queue number and try again.")

st.markdown(
    """
    <style>
    .fixed-bottom {
        position: fixed;
        bottom: 0;
        width: 100%;
        text-align: center;
        padding: 10px;
        z-index: 1000;
    }
    </style>
    
    <div class="fixed-bottom">
        <a href="dingtalk://dingtalkclient/action/sendmsg?dingtalk_id=umt_dlvnji54w" 
           data-spm-click="gostr=/nw;locaid=dingtalk-icon" 
           data-spm-anchor-id="0.0.0.dingtalk-icon">
            <img src="https://cdn-icons-png.flaticon.com/512/906/906381.png" 
                 alt="DingTalk Icon" 
                 style="width:32px; height:32px; vertical-align: middle;">
            开发人员
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

logging.debug("App finished.")