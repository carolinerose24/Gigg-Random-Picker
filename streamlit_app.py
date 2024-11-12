import streamlit as st
import pandas as pd
import requests
import random


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Random User Picker',
    page_icon=':white_check_mark:'
)


@st.cache_data(ttl='1d')
def pull_all_users_from_APIs(token):
    base_url = "https://app.circle.so/api/admin/v2/community_members?per_page=100&page="
    headers = {'Authorization': token}
    df_all = pd.DataFrame(columns=['name', 'email', 'created_at', 'last_seen_at'])
    page = 1  
    while True:
        url = base_url + str(page)
        response = requests.get(url, headers=headers)
        # data = response.json()
        # records = data.get('records', [])

        data = pd.json_normalize(response.json())
        records_list = data['records'][0]
        if not records_list: 
            break
        # df = pd.json_normalize(records)
        df = pd.json_normalize(records_list)
        df = df[['name', 'email', 'created_at', 'last_seen_at']] #comments_count, posts_count, activity_score
        df_all = pd.concat([df_all, df], ignore_index=True)
        # if page % 5 == 0:
        #     st.write("Made the API call for page: " + str(page))
        page += 1
        # time.sleep(0.15)
    df_all['last_seen_at'] = pd.to_datetime(df_all['last_seen_at'])
    df_all['created_at'] = pd.to_datetime(df_all['created_at'])
    # st.write("Made " + str(page) + " API calls.")
    return df_all

def get_random_members(df, number_picks=1, last_seen_option="None",
                        # posts_count=0, comments_count=0,
                        created_option="None", filter_admins=True):#, activity_score=0):
    

    if last_seen_option != "None":
        df = filter_last_seen(df, last_seen_option)
        #call the date function to filter out by certain dates

    if created_option != "None":
        df = filter_account_creation(df, created_option)

    # if posts_count > 0:
    #     df = filter_posts(df, posts_count)

    # if comments_count > 0:
    #     df = filter_comments(df, comments_count)
        
    # if activity_score > 0:
    #     df = filter_activity_score(df, activity_score)
        

    if filter_admins:
        raw_df = pd.DataFrame(df)
        df_no_gigg = raw_df[~raw_df['email'].str.contains('gigg', case=False, na=False)]
        df = df_no_gigg[~df_no_gigg['name'].str.contains('admin', case=False, na=False)]

    st.write(f"There were {len(df)} people in the final group, so the odds were {number_picks}/{len(df)}, or {number_picks / len(df) * 100:.3f}%")

    return pd.DataFrame(df).sample(n=number_picks)


def filter_last_seen(df, date):
    today = pd.Timestamp.now(tz='UTC')
    match date:
        case "Today": #TODAY
            # print(f"Filtering to users that were last seen today:")
            start_of_today = today.normalize()  # Resets time to 00:00:00
            today_filter = df['last_seen_at'] >= start_of_today
            return df.loc[today_filter]

        case "This Week": #THIS WEEK
            # print(f"Filtering to users that were last seen sometime this week:")
            this_week_filter = df['last_seen_at'] >= (today - pd.DateOffset(days=7))
            return df.loc[this_week_filter]

        case "This Month": #THIS MONTH
            # print(f"Filtering to users that were last seen sometime this month:")
            this_month_filter = (df['last_seen_at'] >= pd.to_datetime(f"{today.year}-{today.month}-01", utc=True)) 
            return df.loc[this_month_filter]
                
    #specific date -- do something HERE
    return df


def filter_posts(df, count):
    # print(f"Filtering to users that have made at least {count} post(s):")
    return df.loc[(df['posts_count'] >= count)]


def filter_comments(df, count):
    # print(f"Filtering to users that have made at least {count} comment(s):")
    return df.loc[(df['posts_count'] >= count)]


def filter_account_creation(df, date):
    today = pd.Timestamp.now(tz='UTC')
    match date:
        case "This Month":
            # print(f"Filtering to users that became members this month:")
            this_month_filter = (df['created_at'] >= pd.to_datetime(f"{today.year}-{today.month}-01", utc=True)) 
            return df.loc[this_month_filter]
        case "Last Two Months":
            # print(f"Filtering to users that became members this or last month:")
            last_month_start = pd.to_datetime(f"{today.year}-{today.month - 1}-01", utc=True) if today.month > 1 else pd.to_datetime(f"{today.year - 1}-12-01", utc=True)
            last_two_months_filter = df['created_at'] >= last_month_start
            return df.loc[last_two_months_filter]
        case "On Launch":
            # print(f"Filtering to users that became members in the launch month (May 2024):")
            #May 2024
            start_date = pd.to_datetime("2024-05-01", utc=True)
            end_date = pd.to_datetime("2024-05-31 23:59:59", utc=True)
            may_users_filter = (df['created_at'] >= start_date) & (df['created_at'] <= end_date)
            return df.loc[may_users_filter]

    # filter by a specific date??
    return df


def filter_activity_score(df, score):
    # print(f"Filtering to users that have an activity score of at least {score}:")
    return df.loc[(df['activity_score'] >= score)]
    

def check_community(token):
    #can't get the community name anywhere? could just return the community ID for now???
    url = "https://app.circle.so/api/admin/v2/community_members?per_page=1&page=1"
    headers = {'Authorization': token}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = pd.json_normalize(response.json())
        records_list = data['records'][0]  
        df = pd.json_normalize(records_list)
        return df['community_id'][0]
    else:
        return response.status_code
    
members = pd.DataFrame(columns=['name', 'email', 'created_at', 'last_seen_at'])



# ------------------------------------------------------------------------------------------

'''
# Random User Picker:
This is an app for picking a random user from a circle community based on a few filters. It may take a couple minutes to pull all the users from the API the first time you make a random user request, but it should be much faster each time after that.

### To Get Your Token:
To use this app, you need a Circle Admin V2 Token. If you are an admin for a community, you can click on the community name/drop down in the top left corner of the community site. 
If you navigate to the developer's page and then the token page, you can create a V2 token (not V1 or Headless or Data!!). 
You only need to create a V2 token once for each community because you can always use the same token after that.
'''

#button to show images or not?? or slider...
on = st.toggle("Show Help Images")

if on:
    # st.image("https://drive.google.com/file/d/1mn7IfedKYgZugI7EQm4_QIKhmUmVlDBQ/view?usp=drive_link", caption = "Admin Dropdown Menu", width=250)
    # st.image("https://drive.google.com/file/d/1SqmincwR7HcDd1hZ4rCMgaHmUE6Q6UxM/view?usp=drive_link", caption = "Developer Dropdown Menu", width=250)
    # st.image("https://drive.google.com/file/d/1jj4Vn4FVhC9fA7ebBSTfJWXcJNuupNhU/view?usp=drive_link", caption = "Token Creation Page")
    st.image("images/admin_dropdown.png", caption = "Admin Dropdown Menu", width=250)
    st.image("images/tokens.png", caption = "Developer Dropdown Menu", width=250)
    st.image("images/create_token.png", caption = "Token Creation Page")




token = "Token " + st.text_input("Paste your Admin V2 Community Token here, then press enter to check if it is a valid token.", "")
if token != "Token ":

    #if checking the token is valid, print that it is valid, otherwise print something about it being invalid
    token_response = str(check_community(token))
    if token_response == '401':
        st.write("Invalid Token! Please try again.")
    else:
        st.write("Valid Token for the community with the id: " + str(check_community(token))) 
else:
    members = st.empty()
    

with st.form("my_form"):
   st.write("Choose the filters you want here: (choose none if you don't want to use a filter)")
   picks = st.number_input(
        label = "How many random users do you want to pick?", 
        min_value=1, max_value=20, value="min"
    )
   last_seen_pick = st.selectbox(
        "Filter by the last time a user visited the community site?",
        ("None", "Today", "This Week", "This Month"),
    ) # (Last Seen Date)
   account_created_pick = st.selectbox(
        "Filter by the date of account creation?",
        ("None", "This Month", "Last 2 Months", "On Launch")
    )   # (Filter to members who made their account...)
   filter_admins_check = st.checkbox("Filter out Admins and Gigg accounts", value = True)
   
   submit = st.form_submit_button('Submit my picks')


if submit:
    members = pull_all_users_from_APIs(token)
    try:
        picks_df = get_random_members(members, number_picks=picks, last_seen_option=last_seen_pick, created_option=account_created_pick, filter_admins=filter_admins_check)
        picks_df.reset_index(drop=True, inplace=True)
        st.dataframe(picks_df[['name', 'email']], width=400)
    except ValueError as e:
        st.error(f"There are not {picks} members that fit these parameters. Please try a smaller number or choose different filters. ")

