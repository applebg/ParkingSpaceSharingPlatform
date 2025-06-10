'''This file intends to generate fake data for database.\n
table dependence is this:\n
users -> parking_lots -> timeintervals\n
users -> borrowers
'''
from faker import Faker
import random
import datetime
from app import db, app, parking_lot, link_reg_parking_lot, all_set_back_to_empty_unbooked
from app import User, ParkingLotRegistration, TimeInterval, Borrower #models
from sqlalchemy.orm import Session

# note that I need to adjust parking lot numbers in create_parking_lots() to tune supply

# Initialize Faker
faker = Faker()

# These contants affect the following functions
NUM_USERS = 50 # how many users to create
NUM_OWNERS = 50
NUM_BORROWERS = 50
NUM_PARKING_LOTS = 50 # how many parking lots to create
YEAR = 2024 # the year, month and day of time intervals
MONTH = 11
DAY = 22

def create_users():
    """Generate users with roles 'owner' and 'borrower'."""
    users = []
    for _ in range(NUM_OWNERS): #geneate owners
        role = "owner"
        user = User(
            username=faker.unique.user_name(),
            password=faker.password(),
            role=role
        )
        users.append(user)
    for _ in range(NUM_BORROWERS): # generate borrowers
        role = "borrower"
        user = User(
            username=faker.unique.user_name(),
            password=faker.password(),
            role=role
        )
        users.append(user)
    db.session.bulk_save_objects(users)
    db.session.commit()
    print(f"{NUM_OWNERS} onwers, {NUM_BORROWERS} borrowers created.")

def create_parking_lots():
    """Generate parking lots linked to owners."""
    all_set_back_to_empty_unbooked() # make sure parking lot area is reset
    
    owners = User.query.filter_by(role='owner').all() # get all owners
    lots = []
    available_lots = parking_lot.report_coordinate(target=1) # report the coordinate of empty unbooked parking lots
    available_lots = available_lots[0:NUM_PARKING_LOTS]
    available_lots_num = len(available_lots)
    for _ in range(len(available_lots)): # either NUM_LOTS or num of available lots
        owner = random.choice(owners)
        available_lot_tuple = available_lots.pop() # pop a tuple
        available_lot_str = str(available_lot_tuple) #convert to str
        lot = ParkingLotRegistration(
            name=owner.username,

            owned_parking_lot=available_lot_str,
            empty=True,
            booked=False,
            user_id=owner.id
        )
        lots.append(lot)
    db.session.bulk_save_objects(lots)
    db.session.commit()
    print(f"{available_lots_num} parking lots created.")
    link_reg_parking_lot()

def create_time_intervals():
    """Generate non-overlapping time intervals linked to parking lots."""
    parking_lots = ParkingLotRegistration.query.all()
    intervals = []

    for lot in parking_lots:
        available_blocks = [(8, 18)]  # Time blocks in hours: 08:00 to 18:00
        lot_intervals = []

        while available_blocks:
            # Select a block randomly
            block_start, block_end = random.choice(available_blocks)
            duration = random.randint(1, 10)  # Interval duration between 1 and 10 hours

            # Ensure start_time and end_time fit within the current block
            if (block_end - block_start) < duration:
                available_blocks.remove((block_start, block_end))  # Block is too small; remove it
                continue

            start_hour = random.randint(block_start, block_end - duration)
            end_hour = start_hour + duration

            # Create a time interval
            interval = TimeInterval(
                start_time=datetime.datetime.now().replace(
                    year=YEAR, month=MONTH, day=DAY, hour=start_hour, minute=0, second=0, microsecond=0
                ),
                end_time=datetime.datetime.now().replace(
                    year=YEAR, month=MONTH, day=DAY, hour=end_hour, minute=0, second=0, microsecond=0
                ),
                parking_lot_id=lot.id
            )
            lot_intervals.append(interval)

            # Update available blocks
            available_blocks.remove((block_start, block_end))
            if block_start < start_hour:  # Add the block before the new interval
                available_blocks.append((block_start, start_hour))
            if end_hour < block_end:  # Add the block after the new interval
                available_blocks.append((end_hour, block_end))

        intervals.extend(lot_intervals)

    # Save to database
    db.session.bulk_save_objects(intervals)
    db.session.commit()
    print(f"{len(intervals)} time intervals created.")

def create_time_intervals_check_overlap():
    '''check if create_time_intervals() created overlapping time intervals or not'''
    intervals = TimeInterval.query.all()
    for i1 in intervals:
        for i2 in intervals:
            if i1.id != i2.id and i1.parking_lot_id == i2.parking_lot_id:
                if not (i1.end_time <= i2.start_time or i1.start_time >= i2.end_time):
                    print(f"Overlap detected: {i1} overlaps with {i2}")

def create_borrowers():
    """Generate borrowers linked to user accounts without overlapping time intervals."""
    borrowers = User.query.filter_by(role='borrower').all()  # Get all borrower accounts
    requests = []

    time_slots = {}  # Dictionary to track used time intervals for each borrower
    
    for borrower_user in borrowers:
        # Initialize time slots for each borrower
        if borrower_user.id not in time_slots:
            time_slots[borrower_user.id] = []

        attempts = 0  # Avoid infinite loops when generating time intervals
        while len(time_slots[borrower_user.id]) < random.randint(1, 3):  # Generate 1-3 time intervals per borrower
            if attempts > 100:  # Safety limit for retries
                break

            # Generate a candidate time interval
            start_hour = random.randint(8, 17)  # Start time between 08:00 and 17:00
            duration = random.randint(1, 10)  # Duration of 1-3 hours
            end_hour = start_hour + duration

            if end_hour > 18:  # Ensure the end time doesn't exceed 18:00
                continue

            start_time = datetime.datetime.now().replace(
                year=YEAR, month=MONTH, day=DAY, hour=start_hour, minute=0, second=0, microsecond=0
            )
            end_time = datetime.datetime.now().replace(
                year=YEAR, month=MONTH, day=DAY, hour=end_hour, minute=0, second=0, microsecond=0
            )

            # Check for overlap with existing time intervals
            overlap = False
            for existing_start, existing_end in time_slots[borrower_user.id]:
                if not (end_time <= existing_start or start_time >= existing_end):
                    overlap = True
                    break

            if overlap:
                attempts += 1
                continue  # Skip this interval if overlap detected

            # Add the valid time interval
            borrower = Borrower(
                name=borrower_user.username,
                start_time=start_time,
                end_time=end_time,
                user_id=borrower_user.id
            )
            requests.append(borrower)

            # Record this time slot for overlap checking
            time_slots[borrower_user.id].append((start_time, end_time))

    # Save to the database
    db.session.bulk_save_objects(requests)
    db.session.commit()
    print(f"{len(requests)} borrowers created with non-overlapping time intervals.")

if __name__ == "__main__":
    with app.app_context():
        db.create_all() # create all tables
        create_users()
        create_parking_lots()
        create_time_intervals()
        create_borrowers()
        # print("Test data generation complete.")
        # Query all intervals for a specific parking lot