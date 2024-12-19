import streamlit as st
import pandas as pd
import requests
import random
import matplotlib.pyplot as plt


# Set the title and favicon that appear in the Browser's tab bar.
st.set_page_config(
    page_title='Random User Picker',
    page_icon=':white_check_mark:'
)


@st.cache_data(ttl='1d')
def pull_all_users_from_APIs(token):
    base_url = "https://app.circle.so/api/admin/v2/community_members?per_page=100&page="
    headers = {'Authorization': "Token " + token}
    df_all = pd.DataFrame(columns=['name', 'email', 'created_at', 'last_seen_at'])
    page = 1  
    while True:
        url = base_url + str(page)
        response = requests.get(url, headers=headers)
        data = pd.json_normalize(response.json())
        records_list = data['records'][0]
        if not records_list: 
            break
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


# Add filter by people's name starting with XX letters


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
    headers = {'Authorization': "Token " + token}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = pd.json_normalize(response.json())
        records_list = data['records'][0]  
        df = pd.json_normalize(records_list)
        return df['community_id'][0]
    else:
        return 0
    

def members_last_seen_graph(df):
    # Last Seen Chart

    today = pd.Timestamp.now(tz='UTC')
    start_of_today = today.normalize()  # Resets time to 00:00:00
    today_filter = df['last_seen_at'] >= start_of_today
    this_week_filter = (df['last_seen_at'] >= (today - pd.DateOffset(days=today.weekday()))) & ~today_filter
    this_month_filter = (df['last_seen_at'] >= pd.to_datetime(f"{today.year}-{today.month}-01", utc=True)) & ~this_week_filter
    last_month_filter = (df['last_seen_at'].dt.month == (today.month - 1)) & (df['last_seen_at'].dt.year == today.year) & ~this_month_filter

    # Calculate the number of users in each category
    seen_today_count = df[today_filter].shape[0]
    seen_in_last_week_count = df[this_week_filter].shape[0]
    seen_in_last_month_count = df[this_month_filter].shape[0]
    seen_in_last_two_months_count = df[this_month_filter | last_month_filter].shape[0]
    total_users_count = len(df)  # Total users count without any calculation

    # Create a dictionary with the counts for visualization
    data = {
        'Seen Today': seen_today_count,
        'Seen in Last Week': seen_in_last_week_count,
        'Seen in Last Month': seen_in_last_month_count,
        'Seen in Last 2 Months': seen_in_last_two_months_count,
        'Total Users': total_users_count  # Directly setting this to the length of all_users
    }

    # Calculate cumulative values, except for the last column
    cumulative_data = []
    cumulative_sum = 0
    for key in data.keys():
        if key == 'Total Users':
            cumulative_data.append(data[key])  # Append the total users directly
        else:
            cumulative_sum += data[key]
            cumulative_data.append(cumulative_sum)

    plt.figure(figsize=(10, 6))
    bars = plt.bar(data.keys(), cumulative_data, color='#d0ba71')

    for bar in bars:
        yval = bar.get_height()  # Get the height of each bar
        plt.text(bar.get_x() + bar.get_width()/2, yval, int(yval), 
                 ha='center', va='bottom', fontsize=14)  # Display the height on top of the bar
    plt.title('Cumulative Number of Users Last Seen', fontsize=18)
    plt.ylabel('Cumulative Number of Users', fontsize=16)
    plt.xlabel('Time Period', fontsize=16)
    plt.tight_layout()
    st.pyplot(plt)


def accounts_created_graph(df):
    df = df[df['created_at'] >= '2024-01-01']
    df['year_month'] = df['created_at'].dt.to_period('M')
    monthly_user_counts = df.groupby('year_month').size()

    # Plot the data
    plt.figure(figsize=(12, 6))  # Set figure size
    bars = monthly_user_counts.plot(kind='bar', color='#d0ba71')
    for i, count in enumerate(monthly_user_counts):
        plt.text(i, count, int(count), ha='center', va='bottom', fontsize=14)

    # Add labels and title
    plt.title('Number of New Members by Month', fontsize=18)
    plt.ylabel('Number of Users', fontsize=16)
    plt.xlabel('Month', fontsize=16)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(plt)







def search_people(df, included_names):
        # Split the excluded_list string into a list of names (handle spaces and remove empty names)
    names = [name.strip().lower() for name in included_names.split(',') if name.strip()]
    
    # Normalize the 'Author' column to lowercase for comparison
    df['name_normalized'] = df['name'].str.lower()
    
    # Check for names in excluded_names that are not in the DataFrame
    invalid_names = [name for name in names if name not in df['name_normalized'].unique()]
    
    # Create an alert for invalid names
    if invalid_names:
        st.toast(f"Invalid name(s): {', '.join(invalid_names)}")

    # Filter the DataFrame based on exclude flag
    # if exclude:
    #     filtered_df = df[~df['Author_normalized'].isin(excluded_names)]
    # else:
    filtered_df = df[df['name_normalized'].isin(names)]
    
    # Drop the temporary normalized column before returning
    filtered_df = filtered_df.drop(columns=['name_normalized'])
    filtered_df.reset_index(inplace=True, drop=True)

    #also strip the timezone/stuff and just leave the date
    filtered_df['created_at'] = filtered_df['created_at'].dt.date
    filtered_df['last_seen_at'] = filtered_df['last_seen_at'].dt.date
    return filtered_df[['name', 'last_seen_at', 'created_at', 'email']]




members = pd.DataFrame(columns=['name', 'email', 'created_at', 'last_seen_at'])


# ------------------------------------------------------------------------------------------

'''
# Gigg Community Random User Picker:
This is an app for picking a random user from a circle community based on a few filters. It may take a couple minutes to pull all the users from the API the first time you make a random user request.
'''

#link to the other site here?
st.link_button("Link to Post Valuation Page:", "https://gigg-post-valuation.streamlit.app/")



'''
### To Get Your Token:
To use this app, you need a Circle Admin V2 Token. If you are an admin for a community, you can click on the community name/drop down in the top left corner of the community site. 
If you navigate to the developer's page and then the token page, you can create a V2 token (not V1 or Headless or Data!!). 
You only need to create a V2 token once for each community because you can always use the same token after that.
'''

#button to show images or not?? or slider...
# '''
# #### TOGGLE FOR HELP IMAGES
# '''

st.subheader(":red[TOGGLE FOR HELP IMAGES]")

on = st.toggle("Show Help Images")

if on:
    # st.image("https://drive.google.com/file/d/1mn7IfedKYgZugI7EQm4_QIKhmUmVlDBQ/view?usp=drive_link", caption = "Admin Dropdown Menu", width=250)
    # st.image("https://drive.google.com/file/d/1SqmincwR7HcDd1hZ4rCMgaHmUE6Q6UxM/view?usp=drive_link", caption = "Developer Dropdown Menu", width=250)
    # st.image("https://drive.google.com/file/d/1jj4Vn4FVhC9fA7ebBSTfJWXcJNuupNhU/view?usp=drive_link", caption = "Token Creation Page")
    st.image("images/admin_dropdown.png", caption = "Admin Dropdown Menu", width=250)
    st.image("images/tokens.png", caption = "Developer Dropdown Menu", width=250)
    st.image("images/create_token.png", caption = "Token Creation Page")




token = st.text_input("Paste your Admin V2 Community Token here, then press enter to check if it is a valid token.", "")
if token != "":

    #if checking the token is valid, print that it is valid, otherwise print something about it being invalid
    token_response = str(check_community(token))
    if token_response == 0:
        st.write("Invalid Token! Please try again.")
    else:
        st.write("Valid Token for the community with the id: " + str(check_community(token))) 
else:
    members = st.empty()
    token_response = 1
    

with st.form("my_form"):
    st.write("Choose the filters you want here: (choose none if you don't want to use a filter)")
    picks = st.slider("How many random users do you want to pick?", 1, 20, 5)

    last_seen_pick = st.selectbox(
        "Filter by the last time a user visited the community site?",
        ("None", "Today", "This Week", "This Month"),
    ) # (Last Seen Date)
    account_created_pick = st.selectbox(
        "Filter by the date of account creation?",
        ("None", "This Month", "Last 2 Months")
    )   # (Filter to members who made their account...)

    filter_admins_check = st.checkbox("Filter out Admins and Gigg accounts", value = True)
    st.write("Note that this only filters out users with \'admin\' in their username or @gigg.com in their email.")
   
    submit = st.form_submit_button('Submit my picks')


if submit:

    #need to first check if there is a token, and if not use TOAST
    if token_response == 0 or token_response == 1:
        st.toast("Can't pull users with a bad token!!")
    else:
        members = pull_all_users_from_APIs(token)
        try:
            picks_df = get_random_members(members, number_picks=picks, last_seen_option=last_seen_pick, created_option=account_created_pick, filter_admins=filter_admins_check)
            picks_df.reset_index(drop=True, inplace=True)
            st.dataframe(picks_df[['name', 'email']], width=400)
        except ValueError as e:
            st.error(f"There are not {picks} members that fit these parameters. Please try a smaller number or choose different filters. ")




st.divider()
#search a person and get everything back about them......
with st.form("person_search"):
    st.subheader("Person Search")
    st.write("Input a name to see more information about them:")
    included_people = st.text_input("Input exact names here (comma seperated)", "")
    person_submit = st.form_submit_button('Search')
if person_submit:
    
    if token_response == 0 or token_response == 1:
        st.toast("Can't do this with a bad token")
    else:
        members = pull_all_users_from_APIs(token)
        df = search_people(members, included_people)
        st.dataframe(df)
        #would like this to later include # of likes/comments and activity score...

# change this so it runs an API call???
#sort so that when it returns a list it does it alphabetically?
# or sort by most recently seen?????












st.divider()

st.subheader("Things I would like to add eventually (depending on Circle)")
'''
- Activity Score
- Comments Left
- Likes Left
'''



st.divider()

stats_button = st.button("Generate Statistics about your users:")
if stats_button:
    if token_response == 0 or token_response == 1:
        st.toast("Can't pull users with a bad token!!")
    else:
        members = pull_all_users_from_APIs(token)
        st.write(f"There are {len(members)} members in this community.")
        st.write("Here is a cumulative graph showing when members were last seen:")
        members_last_seen_graph(members)
        st.divider()
        accounts_created_graph(members)


        #accounts made by month...
        

    
    #what should i show here
    #total number of users
    #how many last seen today,
    #last seen this week, this month??
    # 


    #when accounts were made X last seen
    #last seen today, this week, this month, after that --> pie chart?

    # growth of account creation --> as people make their accounts
    #how many made it when (bar chart???)
    #



    