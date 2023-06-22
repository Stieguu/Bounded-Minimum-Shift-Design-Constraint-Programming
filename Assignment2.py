import argparse
import sys
import time
import random
import math
import copy

random.seed(42)
sys.setrecursionlimit(5000)

# Create the parser
parser = argparse.ArgumentParser()

# Add arguments
parser.add_argument('--file', type=str, help='The input file')
parser.add_argument('--test', action='store_true', help='A test flag')

# Parse arguments
args = parser.parse_args()

# Access arguments
path_data = args.file
is_test = args.test

if path_data is None:
    path_data = "instances/toy2.dzn"
    path_data = "instances/DataSet1/RandomExample5.dzn"

with open(path_data) as f:
    data = f.read()

vars_lists = data.split(";\n")

time_interval_in_Minutes = int(vars_lists[0].split(" = ")[1])
days = int(vars_lists[1].split(" = ")[1])
demand = [int(x) for x in vars_lists[2].split(" = ")[1][1:-1].split(",")]
shiftTypes = int(vars_lists[3].split(" = ")[1])
minStart = [int(x) for x in vars_lists[4].split(" = ")[1][1:-1].split(",")]
maxStart = [int(x) for x in vars_lists[5].split(" = ")[1][1:-1].split(",")]
minLength = [int(x) for x in vars_lists[6].split(" = ")[1][1:-1].split(",")]
maxLength = [int(x) for x in vars_lists[7].split(" = ")[1][1:-1].split(",")]
maxDuties = float(vars_lists[9].split(" = ")[1])
avgMinutes = int(vars_lists[10].split(" = ")[1])
weightOverCover = int(vars_lists[12].split(" = ")[1])
weightShiftInstances = int(vars_lists[14].split(" = ")[1])

if not is_test:
    print("time_interval_in_Minutes = ", time_interval_in_Minutes)
    print("days = ", days)
    print("demand = ", demand)
    print("shiftTypes = ", shiftTypes)
    print("minStart = ", minStart)
    print("maxStart = ", maxStart)
    print("minLength = ", minLength)
    print("maxLength = ", maxLength)
    print("maxDuties = ", maxDuties)
    print("avgMinutes = ", avgMinutes)
    print("weightOverCover = ", weightOverCover)
    print("weightShiftInstances = ", weightShiftInstances)


# Hard constraint: Fully cover the given demand.
# Hard constraint: Satisfy a given minimum average shift length 
# Soft constraint: Minimize exceeding the demand
# Soft constraint: Minimize the number of different shift instances

# time_interval_in_Minutes is Slotlength for demand, minStart, 
# maxStart, minLength, maxLength, minimumAverageShiftLength

neigborhood_distance = 10

minimumAverageShiftLength = avgMinutes/(maxDuties*time_interval_in_Minutes)

slots_per_day = int(24*60/time_interval_in_Minutes)

if not is_test:
    print("minimumAverageShiftLength = ",minimumAverageShiftLength)
    print("slots_per_day = ",slots_per_day)


# create Possible shifts
shifts = []
for type in range(shiftTypes):
    for start in range(minStart[type], maxStart[type]+1):
        for length in range(minLength[type], maxLength[type]+1):
            shifts.append((start, length))

# variables that can be changed
# assigned[(day, shift)] = number of people assigned to shift on day


def create_new_scedule_fits_hard_constraists(assigned, shift_used):
    # I need last value in case hard constraints are not met
    # otherwise infinet loop because it does not find resonable solution
    #last_assigned = copy.deepcopy(assigned)
    #last_shift_used = copy.deepcopy(shift_used)

    # create new schedule
    if assigned == {}:
        for day in range(days):
            for shift in shifts: 
                max_demand = 0
                shift_start_slot = day * slots_per_day + shift[0]
                shift_end_slot = shift_start_slot + shift[1]
                for slot in range(shift_start_slot, shift_end_slot + 1):
                    if max_demand < demand[slot % len(demand)]:
                        max_demand = demand[slot % len(demand)]

                # number of people assigned to shift on day
                assigned[(day, shift)] = round(random.uniform(0, max_demand))
                shift_used[(day, shift)] = assigned[(day, shift)] != 0

    # else we search for solution in neighborhood
    else:
        for x in range(random.randint(1,neigborhood_distance)):
            # we randomly select a shift to change
            day = random.randint(0, days-1)
            shift = random.choice(shifts)

            #shift = (4, 4)
            # we select the amount to change it
            change = random.choice([-1, 1])
            # we change the shift assignment
            if assigned[(day, shift)] + change >= 0 and assigned[(day, shift)] + change <= max(demand):
                assigned[(day, shift)] = assigned[(day, shift)] + change


            shift_used[(day, shift)] = assigned[(day, shift)] != 0


            
                

    #print("assigned = ", assigned)
    #if random.random() < 10.01:
    #    sys.exit()
            



    total_length = sum(shift[1]*assigned[(day, shift)] for day in range(days) for shift in shifts)
    total_shifts = sum(assigned[(day, shift)] for day in range(days) for shift in shifts)

    # average shift length is at least minimumAverageShiftLength
    if not is_test:
        if not total_length * time_interval_in_Minutes >= int(minimumAverageShiftLength * time_interval_in_Minutes) * total_shifts:

            assigned,shift_used, total_over_coverage, total_shift_instances = create_new_scedule_fits_hard_constraists(assigned, shift_used)
            return assigned,shift_used, total_over_coverage, total_shift_instances

 

    # Cover Demand
    over_coverage = []
    for day in range(days):
        for slot in range(slots_per_day):
            # number of employees that started shift today working during slot
            shifts_today = sum([assigned[(day, shift)] for shift in shifts if (shift[0] <= slot and shift[0] + shift[1] > slot)])
            yesterday = day - 1
            # we wrap around to the last day if day = 0
            if yesterday < 0:
                yesterday = days - 1
            # number of employees that started shift yesterday working during slot
            shifts_yesterday = sum([assigned[(yesterday, shift)] for shift in shifts if (shift[0] + shift[1] - slots_per_day > slot)])
            # we set the over_coverage variables to be the number of extra employees at slot
            over_coverage.append(shifts_today + shifts_yesterday - demand[day*slots_per_day + slot])
            # we add constraint that this must be at least 0, i.e. demand is met at slot
            if not over_coverage[-1] >= 0:
                assigned, shift_used, total_over_coverage, total_shift_instances = create_new_scedule_fits_hard_constraists(assigned, shift_used)
                return assigned,shift_used, total_over_coverage, total_shift_instances

    # sum of the over_coverage for all slots
    total_over_coverage = sum(over_coverage) * time_interval_in_Minutes

    # total shift instances
    total_shift_instances = sum([shift_used[(day, shift)] for day in range(days) for shift in shifts])

    return assigned,shift_used,  total_over_coverage, total_shift_instances

def compute_cost( total_over_coverage, total_shift_instances):
    # cost is the sum of the over_coverage and the number of shift instances
    return weightOverCover * total_over_coverage + weightShiftInstances * total_shift_instances


# Initialize a random solution
assigned = {}
shift_used = {}
assigned,shift_used, total_over_coverage, total_shift_instances = create_new_scedule_fits_hard_constraists(assigned,shift_used)
cost = compute_cost( total_over_coverage, total_shift_instances)

# Set the initial temperature and cooling rate
temperature = 100
cooling_rate = 0.95

# Loop until a stopping criterion is met
while temperature > 1e-6:
    # Generate a new solution by making a small random change
    new_assigned,shift_used, new_total_over_coverage, new_total_shift_instances = create_new_scedule_fits_hard_constraists(assigned,shift_used)

    # Calculate the cost of the new solution
    new_cost = compute_cost(new_total_over_coverage, new_total_shift_instances)

    # Calculate the change in cost
    delta_cost = new_cost - cost

    # If the new solution is better, accept it
    if delta_cost < 0:
        assigned = new_assigned
        total_over_coverage = new_total_over_coverage
        total_shift_instances = new_total_shift_instances
        cost = new_cost
    # If the new solution is worse, accept it with a probability that depends on the temperature and the change in cost
    else:
        probability = math.exp(-delta_cost / temperature)
        if random.random() < probability:
            assigned = new_assigned
            total_over_coverage = new_total_over_coverage
            total_shift_instances = new_total_shift_instances
            cost = new_cost


    # Reduce the temperature
    temperature *= cooling_rate

# Return the best solution found
print("Final cost: ", cost)
print("Total over coverage: ", total_over_coverage)
print("Total shift instances: ", total_shift_instances)
print("Assigned: ", assigned)

