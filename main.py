from ortools.sat.python import cp_model
import argparse
import sys
import time

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
    path_data = "instances/toy1.dzn"
    #path_data = "instances/DataSet1/RandomExample5.dzn"

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

print("Processing ", path_data)
print("time_interval_in_Minutes = ", time_interval_in_Minutes)
print("days = ", days)
print("demand = ", demand)
print("sum(demand) = ", sum(demand))
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

minimumAverageShiftLength = avgMinutes/(maxDuties*time_interval_in_Minutes)
slots_per_day = int(24*60/time_interval_in_Minutes)

print("minimumAverageShiftLength = ",minimumAverageShiftLength)
print("slots_per_day = ",slots_per_day)

# Create the model.
model = cp_model.CpModel()
print("Created CpModel")

# create Possible shifts
shifts = []
for type in range(shiftTypes):
    for start in range(minStart[type], maxStart[type]+1):
        for length in range(minLength[type], maxLength[type]+1):
            shifts.append((start, length))


assigned = {}
shift_used = {}
for day in range(days):
    for shift in shifts: 
        max_demand = 0
        shift_start_slot = day * slots_per_day + shift[0]
        shift_end_slot = shift_start_slot + shift[1]
        for slot in range(shift_start_slot, shift_end_slot + 1):
            if max_demand < demand[slot % len(demand)]:
                max_demand = demand[slot % len(demand)]
        # number of people assigned to shift on day
        assigned[(day, shift)] = model.NewIntVar(0, max_demand, f'x_{day}_{shift}')
        # whether the shift has been assigned to at least one employee
        shift_used[(day, shift)] = model.NewBoolVar(f'shift_used_{day}_{shift}')
        model.Add(assigned[(day, shift)] > 0).OnlyEnforceIf(shift_used[(day, shift)])
        model.Add(assigned[(day, shift)] == 0).OnlyEnforceIf(shift_used[(day, shift)].Not())


total_length = sum(shift[1]*assigned[(day, shift)] for day in range(days) for shift in shifts)
total_shifts = sum(assigned[(day, shift)] for day in range(days) for shift in shifts)

# average shift length is at least minimumAverageShiftLength
if not is_test:
    model.Add(total_length * time_interval_in_Minutes >= int(minimumAverageShiftLength * time_interval_in_Minutes) * total_shifts)


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
        # variables that keeps track of the number of extra employees for each slot
        over_coverage.append(model.NewIntVar(0, 2 * max(demand), f'over_coverage_{day}_{slot}'))
        # we set the over_coverage variables to be the number of extra employees at slot
        model.Add(shifts_today + shifts_yesterday - demand[day*slots_per_day + slot] == over_coverage[-1])
        # we add constraint that this must be at least 0, i.e. demand is met at slot
        model.Add(over_coverage[-1] >= 0)

# sum of the over_coverage for all slots
total_over_coverage = model.NewIntVar(0, 2*max(demand)*days*slots_per_day*time_interval_in_Minutes, "total_over_coverage")
model.Add(total_over_coverage == sum(over_coverage) * time_interval_in_Minutes)

# total shift instances
total_shift_instances = model.NewIntVar(0, days*len(shifts), "total_shift_instances")
model.Add(total_shift_instances == sum(shift_used.values()))

# Objective
if not is_test:
    objective = model.NewIntVar(0, weightOverCover*2*max(demand)*days*slots_per_day*time_interval_in_Minutes + weightShiftInstances*days*len(shifts), "objective")
    model.Add(objective == weightOverCover * total_over_coverage + weightShiftInstances * total_shift_instances)
else:
    objective = model.NewIntVar(0, weightOverCover*2*max(demand)*days*slots_per_day*time_interval_in_Minutes, "objective")
    model.Add(objective == weightOverCover * total_over_coverage)
model.Minimize(objective)

# Create the solver and solve the problem
solver = cp_model.CpSolver()
print("Using CpSolver")

solver.parameters.log_search_progress = True
solver.parameters.max_time_in_seconds = 600.0


stime = time.perf_counter()
status = solver.Solve(model)
rtime = time.perf_counter() - stime
sys.stderr.write(f"Finished processing {path_data} in {rtime}\n")
sys.stderr.write(f"Status = {status}\n")
sys.stderr.write(f"solution = {solver.ObjectiveValue()}\n")



print(f"Finished processing {path_data} in {rtime}")
print(f"Status =  {status}")
print(f"objective value = {solver.ObjectiveValue()}")
print("Over coverage is ", solver.Value(total_over_coverage))
print(f"There are {solver.Value(total_shift_instances)} shift instances ")
for day in range(days):
    for shift in shifts:
        if solver.Value(assigned[(day, shift)]) > 0:
            print(f'Assigned {solver.Value(assigned[(day, shift)])} people to shift {shift} on day {day}')




