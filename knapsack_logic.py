'''This file is intended to implement all knapsack problem logic\n
I will fetch data from database first, and then implement knapsack problem algorithm to try to match owners and borrowers\n
Note that the match result is only indended to notify the borrower of his/her best match information'''

import sqlite3
import pandas as pd
from pulp import LpProblem, LpMinimize, LpVariable, lpSum, PULP_CBC_CMD
from datetime import datetime, timedelta
import logging

# Configure logging for heuristic
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more detailed logs
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("parking_lot_matching.log"),  # Log to a file
        logging.StreamHandler()  # Log to console
    ]
)

def create_data():
    '''Fetch data from database then return the dataframe that I want\n
    note that the format of data fetched from database must not be altered because it will affect the following functions\n
    see the SQL commands for detail'''
    # Path to your SQLite database
    db_path = 'instance/database.db'

    # Connect to the SQLite database
    connection = sqlite3.connect(db_path)

    # Retrieve the list of tables
    query_tables = "SELECT name FROM sqlite_master WHERE type='table';"
    tables = pd.read_sql_query(query_tables, connection)

    # print("Tables in the database:")
    # print(tables)

    # Loop through each table and load its data into a pandas DataFrame for analysis
    # take this code as reference
    # for table_name in tables['name']:
    #     print(f"\nData from table: {table_name}")
    #     query_data = f"SELECT * FROM {table_name};"
    #     df = pd.read_sql_query(query_data, connection)
    #     print(df)

    # join the tables together for owners
    owner_query_str = '''SELECT user_id, username, role, owned_parking_lot, empty, booked, start_time, end_time
    FROM users 
    JOIN parking_lots 
    ON users.id = parking_lots.user_id 
    JOIN timeintervals 
    ON parking_lots.id = timeintervals.parking_lot_id
    WHERE role = "owner" '''
    owner_df = pd.read_sql_query(owner_query_str, connection)


    # join the tables together for borrowers
    owner_query_str = '''SELECT user_id, username, role, start_time, end_time
    FROM users 
    JOIN borrowers
    ON users.id = borrowers.user_id 
    WHERE role = "borrower"'''
    borrower_df = pd.read_sql_query(owner_query_str, connection)


    # Close the database connection
    connection.close()
    return owner_df, borrower_df

def parse_datetime(datetime_str):
    """Converts a datetime string to a Python datetime object."""
    return datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S.%f")

# ILP mathod, currently not used 2024-12-19
def split_interval(start, end, duration):
    """
    Splits an interval into smaller sub-intervals of a given duration.
    
    :param start: Start time of the interval (datetime object).
    :param end: End time of the interval (datetime object).
    :param duration: Duration of each sub-interval (timedelta object).
    :return: List of sub-intervals as (start, end) tuples.
    """
    intervals = []
    current = start
    while current + duration <= end:
        intervals.append((current, current + duration))
        current += duration
    return intervals

def match_owners_and_borrowers_with_splitting(owner_df, borrower_df, sub_interval_duration):
    """
    Matches owners and borrowers with owner intervals split into sub-intervals.
    
    :param owner_df: Pandas DataFrame for owners.
    :param borrower_df: Pandas DataFrame for borrowers.
    :param sub_interval_duration: Duration of each sub-interval (timedelta object).
    :return: Matching results.
    """
    from itertools import product
    
    # Generate sub-intervals for each owner
    sub_intervals = []
    sub_interval_map = {}  # Maps sub-interval index to owner
    for j, owner in owner_df.iterrows():
        owner_start = parse_datetime(owner["start_time"])
        owner_end = parse_datetime(owner["end_time"])
        intervals = split_interval(owner_start, owner_end, sub_interval_duration)
        sub_intervals.extend(intervals)
        sub_interval_map.update({len(sub_intervals) - len(intervals) + k: j for k in range(len(intervals))})
    
    num_borrowers = len(borrower_df)
    num_sub_intervals = len(sub_intervals)

    # Create the problem
    problem = LpProblem("Owner_Borrower_SubInterval_Matching", LpMinimize)

    # Decision variables
    x = [[LpVariable(f"x_{i}_{k}", cat="Binary") for k in range(num_sub_intervals)] for i in range(num_borrowers)]

    # Objective function: Minimize the number of unmatched borrowers
    problem += lpSum(1 - lpSum(x[i][k] for k in range(num_sub_intervals)) for i in range(num_borrowers)), "Minimize_Unmatched"

    # Constraints
    for i, borrower in borrower_df.iterrows():
        borrower_start = parse_datetime(borrower["start_time"])
        borrower_end = parse_datetime(borrower["end_time"])
        
        # Borrower must be assigned to at most one sub-interval
        problem += lpSum(x[i][k] for k in range(num_sub_intervals)) <= 1, f"Borrower_{i}_Assignment"

        for k, (sub_start, sub_end) in enumerate(sub_intervals):
            # Borrower time must fit within sub-interval time
            if not (borrower_start >= sub_start and borrower_end <= sub_end):
                problem += x[i][k] == 0, f"Borrower_{i}_SubInterval_{k}_Constraint"

    # Each sub-interval can have at most one borrower
    for k in range(num_sub_intervals):
        problem += lpSum(x[i][k] for i in range(num_borrowers)) <= 1, f"SubInterval_{k}_Assignment"

    # Solve the problem
    solver = PULP_CBC_CMD(msg=False)
    problem.solve(solver)

    # Process results
    matching = {}
    for i, borrower in borrower_df.iterrows():
        for k, (sub_start, sub_end) in enumerate(sub_intervals):
            if x[i][k].value() == 1:
                matching[i] = sub_interval_map[k]
                break
        else:
            matching[i] = None  # Unmatched borrower

    return matching


def match_onwers_and_borrowers_get_df(solution:dict, borrower_df:pd.DataFrame) -> pd.DataFrame:
    '''given a solution made by match_owners_and_borrowers(), this function generates the dataframe that represents the solution'''
    borrower_df["matched_owner_idx"] = "" # add a new column which represents matched owner index
    for borrower_idx, owner_idx in solution.items():
        if owner_idx is not None:
            borrower_df.loc[borrower_idx, "matched_owner_idx"] = owner_idx
        else:
            borrower_df.loc[borrower_idx, "matched_owner_idx"] = "Unmatched"
    return borrower_df

# note that First Fit and Best Fit are intended to be compared together, they are heuristic algorithms
def first_fit_borrowers_to_owners_with_splitting(borrower_df, owner_df):
    """
    Heuristic Algorithm
    Matches borrowers (items) to owners (bins) using the First Fit heuristic
    and splits owner time intervals to maximize utility of unused time.
    Once a lot is matched and split, the original record is dropped.
    """
    logging.info("Starting First Fit matching process with interval splitting.")

    # Convert time columns to datetime for comparison
    owner_df['start_time'] = pd.to_datetime(owner_df['start_time'])
    owner_df['end_time'] = pd.to_datetime(owner_df['end_time'])
    borrower_df['start_time'] = pd.to_datetime(borrower_df['start_time'])
    borrower_df['end_time'] = pd.to_datetime(borrower_df['end_time'])

    matches = []
    owner_df = owner_df.copy()

    for _, borrower in borrower_df.iterrows():
        logging.info(f"Processing borrower ID {borrower['user_id']} ({borrower['username']}), "
                     f"requested time: {borrower['start_time']} to {borrower['end_time']}.")

        # Filter available parking lots that can accommodate the borrower's time slot
        available_lots = owner_df[
            (owner_df['empty'] == 1) &
            (borrower['start_time'] >= owner_df['start_time']) &
            (borrower['end_time'] <= owner_df['end_time'])
        ].copy()

        if not available_lots.empty:
            # Select the first available parking lot
            first_fit_lot = available_lots.iloc[0]
            
            logging.info(f"Match found: Borrower {borrower['username']} -> Parking lot {first_fit_lot['owned_parking_lot']} "
                         f"owned by {first_fit_lot['username']}.")

            # Add match to results
            matches.append({
                'borrower_id': borrower['user_id'],
                'borrower_username': borrower['username'],
                'assigned_lot': first_fit_lot['owned_parking_lot'],
                'owner_id': first_fit_lot['user_id'],
                'owner_username': first_fit_lot['username'],
                'borrower_start': borrower['start_time'],
                'borrower_end': borrower['end_time'],
                'lot_start': first_fit_lot['start_time'],
                'lot_end': first_fit_lot['end_time']
            })

            # Drop the original matched slot
            owner_df = owner_df.drop(first_fit_lot.name)

            # Split the owner's time slot into unused intervals if needed
            new_intervals = []
            if borrower['start_time'] > first_fit_lot['start_time']:
                new_intervals.append({
                    'user_id': first_fit_lot['user_id'],
                    'username': first_fit_lot['username'],
                    'owned_parking_lot': first_fit_lot['owned_parking_lot'],
                    'start_time': first_fit_lot['start_time'],
                    'end_time': borrower['start_time'],
                    'empty': 1,
                    'booked': 0
                })

            if borrower['end_time'] < first_fit_lot['end_time']:
                new_intervals.append({
                    'user_id': first_fit_lot['user_id'],
                    'username': first_fit_lot['username'],
                    'owned_parking_lot': first_fit_lot['owned_parking_lot'],
                    'start_time': borrower['end_time'],
                    'end_time': first_fit_lot['end_time'],
                    'empty': 1,
                    'booked': 0
                })

            # Append newly split intervals back to owner_df
            if new_intervals:
                owner_df = pd.concat([owner_df, pd.DataFrame(new_intervals)], ignore_index=True)
        else:
            logging.warning(f"No available parking lot for borrower {borrower['username']}.")

    logging.info("First Fit matching process with interval splitting completed.")
    return pd.DataFrame(matches)

def best_fit_borrowers_to_owners_with_splitting(borrower_df, owner_df):
    """
    Heuristic Algorithm
    Matches borrowers (items) to owners (bins) using the Best Fit heuristic
    and splits owner time intervals to maximize utility of unused time.
    Once a lot is matched and split, the original record is dropped.
    """
    logging.info("Starting Best Fit matching process with interval splitting.")

    # Convert time columns to datetime for comparison
    owner_df['start_time'] = pd.to_datetime(owner_df['start_time'])
    owner_df['end_time'] = pd.to_datetime(owner_df['end_time'])
    borrower_df['start_time'] = pd.to_datetime(borrower_df['start_time'])
    borrower_df['end_time'] = pd.to_datetime(borrower_df['end_time'])

    matches = []
    owner_df = owner_df.copy()

    for _, borrower in borrower_df.iterrows():
        logging.info(f"Processing borrower ID {borrower['user_id']} ({borrower['username']}), "
                     f"requested time: {borrower['start_time']} to {borrower['end_time']}.")

        # Filter available parking lots that can accommodate the borrower's time slot
        available_lots = owner_df[
            (owner_df['empty'] == 1) &
            (borrower['start_time'] >= owner_df['start_time']) &
            (borrower['end_time'] <= owner_df['end_time'])
        ].copy()

        if not available_lots.empty:
            # Calculate unused time for each parking lot
            available_lots['unused_time'] = (
                (available_lots['end_time'] - borrower['end_time']).dt.total_seconds() +
                (borrower['start_time'] - available_lots['start_time']).dt.total_seconds()
            )
            
            # Select the parking lot with the least unused time
            best_fit_lot = available_lots.loc[available_lots['unused_time'].idxmin()]
            best_fit_lot_hour = best_fit_lot['unused_time'] / 60 / 60  # Convert seconds to hours

            logging.info(f"Best match found: Borrower {borrower['username']} -> Parking lot {best_fit_lot['owned_parking_lot']} "
                         f"owned by {best_fit_lot['username']}, with unused time: {best_fit_lot_hour} hours.")

            # Add match to results
            matches.append({
                'borrower_id': borrower['user_id'],
                'borrower_username': borrower['username'],
                'assigned_lot': best_fit_lot['owned_parking_lot'],
                'owner_id': best_fit_lot['user_id'],
                'owner_username': best_fit_lot['username'],
                'borrower_start': borrower['start_time'],
                'borrower_end': borrower['end_time'],
                'lot_start': best_fit_lot['start_time'],
                'lot_end': best_fit_lot['end_time']
            })

            # Drop the original matched slot
            owner_df = owner_df.drop(best_fit_lot.name)

            # Split the owner's time slot into unused intervals if needed
            new_intervals = []
            if borrower['start_time'] > best_fit_lot['start_time']:
                new_intervals.append({
                    'user_id': best_fit_lot['user_id'],
                    'username': best_fit_lot['username'],
                    'owned_parking_lot': best_fit_lot['owned_parking_lot'],
                    'start_time': best_fit_lot['start_time'],
                    'end_time': borrower['start_time'],
                    'empty': 1,
                    'booked': 0
                })

            if borrower['end_time'] < best_fit_lot['end_time']:
                new_intervals.append({
                    'user_id': best_fit_lot['user_id'],
                    'username': best_fit_lot['username'],
                    'owned_parking_lot': best_fit_lot['owned_parking_lot'],
                    'start_time': borrower['end_time'],
                    'end_time': best_fit_lot['end_time'],
                    'empty': 1,
                    'booked': 0
                })

            # Append newly split intervals back to owner_df
            if new_intervals:
                owner_df = pd.concat([owner_df, pd.DataFrame(new_intervals)], ignore_index=True)
        else:
            logging.warning(f"No available parking lot for borrower {borrower['username']}.")

    logging.info("Best Fit matching process with interval splitting completed.")
    return pd.DataFrame(matches)

def statistics(matched_df, borrower_df, owner_df):
    """Generate a report on matching statistics."""
    borrower_count = len(borrower_df)
    total_required_time = pd.Series.sum(pd.to_datetime(borrower_df['end_time']) - pd.to_datetime(borrower_df['start_time']))
    total_required_time = total_required_time.total_seconds() / 3600

    total_provided_time = pd.Series.sum(pd.to_datetime(owner_df['end_time']) - pd.to_datetime(owner_df['start_time']))
    total_provided_time = total_provided_time.total_seconds() / 3600

    matched_count = len(matched_df)
    total_matched_time = pd.Series.sum(pd.to_datetime(matched_df['borrower_end']) - pd.to_datetime(matched_df['borrower_start']))
    total_matched_time = total_matched_time.total_seconds() / 3600

    matched_ratio = matched_count / borrower_count if borrower_count else 0
    utilization = total_matched_time / total_provided_time if total_provided_time else 0

    report = {}
    report["Borrower Records"] = borrower_count
    report["Total Required Time (hours)"] = total_required_time
    report["Total Provided Time (hours)"] = total_provided_time
    report["Matched Borrowers"] = matched_count
    report["Total Matched Time (hours)"] = total_matched_time
    report["Match Ratio"] = matched_ratio
    report["Space Utilization"] = utilization
    
    return report

owner_df, borrower_df = create_data() # fetch data first!

# block for match_owners_and_borrowers #
# Solve the matching problem
# ILP_solution = match_owners_and_borrowers(owner_df = owner_df.copy(), borrower_df = borrower_df.copy())
# ILP_solution_df = match_onwers_and_borrowers_get_df(solution=ILP_solution, borrower_df=borrower_df)
# print(ILP_solution_df)


if __name__ == "__main__":

    # print(borrower_df)

    # block for first_fit_borrowers_to_owners #
    first_fit_df = first_fit_borrowers_to_owners_with_splitting(borrower_df = borrower_df.copy(), owner_df = owner_df.copy())
    # print(first_fit_df)

    # block for best_fit_borrowers_to_owners #
    best_fit_df = best_fit_borrowers_to_owners_with_splitting(borrower_df = borrower_df.copy(), owner_df = owner_df.copy())
    # print(best_fit_df)

    ff_stat = statistics(matched_df = first_fit_df.copy(), borrower_df = borrower_df.copy(), owner_df = owner_df.copy())
    bf_stat = statistics(matched_df = best_fit_df.copy(), borrower_df = borrower_df.copy(), owner_df = owner_df.copy())

    print(ff_stat)
    print(bf_stat)
    # ILP_solution = match_owners_and_borrowers_with_splitting(owner_df = owner_df.copy(), borrower_df = borrower_df.copy(), sub_interval_duration=timedelta(hours = 1))
    # ILP_solution_df = match_onwers_and_borrowers_get_df(solution=ILP_solution, borrower_df=borrower_df)
