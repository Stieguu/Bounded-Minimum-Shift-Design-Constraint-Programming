from ortools.sat.python import cp_model

path_data = "instances/toy1.dzn"
#path_data = "instances/DataSet1/RandomExample1.dzn"

with open(path_data) as f:
    data = f.read()

vars_lists = data.split(";\n")

time_interval_in_Minutes = int(vars_lists[0].split(" = ")[1])
print("time_interval_in_Minutes = ", time_interval_in_Minutes)
days = int(vars_lists[1].split(" = ")[1])
print("days = ", days)
demand = [int(x) for x in vars_lists[2].split(" = ")[1][1:-1].split(",")]
print("demand = ", demand)
shiftTypes = int(vars_lists[3].split(" = ")[1])
print("shiftTypes = ", shiftTypes)
minStart = [int(x) for x in vars_lists[4].split(" = ")[1][1:-1].split(",")]
print("minStart = ", minStart)
maxStart = [int(x) for x in vars_lists[5].split(" = ")[1][1:-1].split(",")]
print("maxStart = ", maxStart)
minLength = [int(x) for x in vars_lists[6].split(" = ")[1][1:-1].split(",")]
print("minLength = ", minLength)
maxLength = [int(x) for x in vars_lists[7].split(" = ")[1][1:-1].split(",")]
print("maxLength = ", maxLength)
maxDuties = int(vars_lists[9].split(" = ")[1])
print("maxDuties = ", maxDuties)
avgMinutes = int(vars_lists[10].split(" = ")[1])
print("avgMinutes = ", avgMinutes)
weightOverCover = int(vars_lists[12].split(" = ")[1])
print("weightOverCover = ", weightOverCover)
weightShiftInstances = int(vars_lists[14].split(" = ")[1])
print("weightShiftInstances = ", weightShiftInstances)

# Hard constraint: Fully cover the given demand.
# Hard constraint: Satisfy a given minimum average shift length 
# Soft constraint: Minimize exceeding the demand
# Soft constraint: Minimize the number of different shift instances

# time_interval_in_Minutes is Slotlength for demand, minStart, 
# maxStart, minLength, maxLength, minimumAverageShiftLength

minimumAverageShiftLength = avgMinutes/(maxDuties*time_interval_in_Minutes)
print("minimumAverageShiftLength = ",minimumAverageShiftLength)
minimumAverageShiftLengthInMinutes = avgMinutes/maxDuties
print("minimumAverageShiftLengthInMinutes = ",minimumAverageShiftLengthInMinutes)
slots_per_day = int(24*60/time_interval_in_Minutes)
print("slots_per_day = ",slots_per_day)

# Create the model.
model = cp_model.CpModel()

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
        # number of people assigned to shift on day
        assigned[(day, shift)] = model.NewIntVar(0, max(demand), f'x_{day}_{shift}')
        # whether the shift has been assigned to at least one employee
        shift_used[(day, shift)] = model.NewBoolVar(f'shift_used_{day}_{shift}')
        model.Add(assigned[(day, shift)] > 0).OnlyEnforceIf(shift_used[(day, shift)])
        model.Add(assigned[(day, shift)] == 0).OnlyEnforceIf(shift_used[(day, shift)].Not())


total_length = sum(shift[1]*assigned[(day, shift)] for day in range(days) for shift in shifts)
total_shifts = sum(assigned[(day, shift)] for day in range(days) for shift in shifts)

# average shift length is at least minimumAverageShiftLength
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
        over_coverage.append(model.NewIntVar(0, max(demand), f'over_coverage_{day}_{slot}'))
        # we set the over_coverage variables to be the number of extra employees at slot
        model.Add(shifts_today + shifts_yesterday - demand[day*slots_per_day + slot] == over_coverage[-1])
        # we add constraint that this must be at least 0, i.e. demand is met at slot
        model.Add(over_coverage[-1] >= 0)

# sum of the over_coverage for all slots
total_over_coverage = model.NewIntVar(0, weightOverCover*max(demand)*days*slots_per_day, "total_over_coverage")
model.Add(total_over_coverage == sum(over_coverage))

# total shift instances
total_shift_instances = model.NewIntVar(0, weightShiftInstances*days*len(shifts), "total_shift_instances")
model.Add(total_shift_instances == sum(shift_used.values()))

# Objective
objective = model.NewIntVar(0, weightOverCover*max(demand)*days*slots_per_day + weightShiftInstances*days*len(shifts), "objective")
model.Add(objective == weightOverCover * total_over_coverage + weightShiftInstances * total_shift_instances)
model.Minimize(objective)

# Create the solver and solve the problem
solver = cp_model.CpSolver()
solver.parameters.log_search_progress = True
status = solver.Solve(model)

# Print the solution
if status == cp_model.OPTIMAL:
    print(f'Optimal solution found with objective value {solver.ObjectiveValue()}')
    print(f'Number of shift hours in demand: {sum(demand)} and factor weightOverCover: {weightOverCover}')
    print(f'factor weightShiftInstances: {weightShiftInstances}')

    for day in range(days):
        for shift in shifts:
            if solver.Value(assigned[(day, shift)]) > 0:
                print(f'Assigned {solver.Value(assigned[(day, shift)])} people to shift {shift} on day {day}')
            #for i in range(max(demand)):
            #    if solver.Value(assigned[(day, shift, i)]) == 1:
            #        print(f'Assigned {i} people to shift {shift} on day {day}')

else:
    print('No solution found')
    print(solver.ResponseStats())



