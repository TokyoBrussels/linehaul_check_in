import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import logging
from datetime import datetime
import pytz

timezone = pytz.timezone('Asia/Bangkok')

st.set_page_config(
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

    tabs = st.tabs(["🟢 CHECK-IN", "🟢 REPLACEMENT", "🟢 ADMIN"])

    with tabs[0]:
        st.header("CHECK-IN")

        truck_id = st.text_input("Enter Truck ID:")

        if truck_id:
            logging.debug(f"Truck ID entered: {truck_id}")
            truck_data = df[df['truck_id'] == truck_id]

            if not truck_data.empty:
                logging.info(f"Truck data found: {truck_id}")
                st.write("Truck Details:")

                truck_info = {
                    "Origin Node": truck_data.iloc[0]['origin_node'],
                    "Vendor": truck_data.iloc[0]['vendor_name'],
                    "Driver": truck_data.iloc[0]['driver_name'],
                    "Driver Contact": truck_data.iloc[0]['driver_tel'],
                    "Truck Type": truck_data.iloc[0]['vehicle_type'],
                    "Status": truck_data.iloc[0]['status'],
                    "Estimated Time Of Arrival": truck_data.iloc[0]['eta_ts'],
                    "Check-In Time": truck_data.iloc[0]['check_in_ts'],
                    "Replacement Truck": truck_data.iloc[0]['replace_truck_id']
                }

                df_truck_info = pd.DataFrame(truck_info.items(), columns=['Detail', 'Value'])
                st.table(df_truck_info)

                current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")

                if st.button("Check-in"):
                    logging.debug("Check-in button pressed.")
                    row = df[df['truck_id'] == truck_id].index
                    if not row.empty:
                        current_status = truck_data.iloc[0]['status']
                        if pd.notna(current_status) and current_status != '':
                            st.warning(f"Check-in blocked: Truck {truck_id} already has a status: '{current_status}'.")
                            logging.warning(f"Check-in blocked for truck {truck_id} with existing status: '{current_status}'")
                        else:
                            user_id = st.session_state.user_id
                            current_time = datetime.now(timezone).strftime("%Y-%m-%d %H:%M:%S")
                            eta_time = pd.to_datetime(truck_data.iloc[0]['eta_ts'])
                            current_time_obj = pd.to_datetime(current_time)

                            time_difference = (eta_time - current_time_obj).total_seconds() / 3600

                            if current_time_obj > eta_time:
                                status = "late_check_in"
                            elif current_time_obj < eta_time and time_difference < 2:
                                status = "onTime_check_in"
                            else:
                                status = "early_check_in"

                            main_sheet.update_cell(row[0] + 2, df.columns.get_loc('check_in_ts') + 1, current_time)
                            main_sheet.update_cell(row[0] + 2, df.columns.get_loc('status') + 1, status)
                            main_sheet.update_cell(row[0] + 2, df.columns.get_loc('update_by') + 1, user_id)

                            st.success(f"Check-in time recorded: {current_time}, Status updated to '{status}'.")
                            logging.info(f"Check-in time and status updated for {truck_id}: {current_time}, '{status}'")
                    else:
                        st.warning("Truck ID not found, please check the ID and try again.")
                        logging.warning(f"Failed check-in, truck ID not found: {truck_id}")

    with tabs[1]:
        st.header("REPLACEMENT")
        
        with st.form("replace_form"):
            replace_truck_id = st.text_input("Replacement Truck ID:")
            new_truck_id = st.text_input("New Truck ID:")
            origin_node = st.selectbox("Origin Node Name:", ["SSW", "TPK"])
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
                            user_id  
                        ]
                            
                        try:
                            main_sheet.append_row(new_row)
                            row_A = df[df['truck_id'] == replace_truck_id].index         
                            if not row_A.empty:
                                main_sheet.update_cell(row_A[0] + 2, df.columns.get_loc('status') + 1, f"replace_by_{new_truck_id}")
            
                                st.success(f"New truck {new_truck_id} successfully logged as a replacement for {replace_truck_id}. Status updated to 'replace_by_{new_truck_id}', updated by {user_id}.")
                                logging.info(f"New truck {new_truck_id} logged for replacement of {replace_truck_id}, status updated to 'replace_by_{new_truck_id}', updated by {user_id}.") 
                                    
                        except Exception as e:
                            st.error(f"Failed to log new truck: {e}")
                            logging.error(f"Failed to log new truck for {replace_truck_id}: {e}")
                else:
                    st.error("Replacement Truck ID not found in records.")

st.markdown(
    """
    <style>
    .fixed-bottom {
        position: fixed;
        bottom: 0;
        width: 40%;
        text-align: center;
        padding: 10px;
        z-index: 1000;
    }
    </style>
    
    <div class="fixed-bottom">
        <a href="dingtalk://dingtalkclient/action/sendmsg?dingtalk_id=umt_dlvnji54w" 
           data-spm-click="gostr=/nw;locaid=dingtalk-icon" 
           data-spm-anchor-id="0.0.0.dingtalk-icon">
            <img src="https://img.alicdn.com/imgextra/i3/O1CN01NRbmMV1bqpjKrW9Go_!!6000000003517-55-tps-12-16.svg" 
                 alt="DingTalk Icon" 
                 style="width:24px; height:32px; vertical-align: middle;">
            Feedback
        </a>
    </div>
    """,
    unsafe_allow_html=True
)

logging.debug("App finished.")