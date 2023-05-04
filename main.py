from ortools.sat.python import cp_model

path_data = "instances/toy1.dzn"
#path_data = "instances/DataSet1/RandomExample1.dzn"

with open(path_data) as f:
    data = f.read()

vars_lists = data.split(";\n")

print(vars_lists)

# ['interval = 60', 'days = 7', 'demand = [0,0,0,0,0,0,0,3,11,11,12,18,18,18,15,11,11,7,7,2,0,0,1,1,1,1,1,1,1,1,0,5,13,13,14,20,20,20,15,11,11,7,7,2,0,0,1,1,1,1,1,1,1,1,0,5,13,13,14,20,20,20,15,11,11,7,7,2,0,0,2,2,2,2,2,2,2,2,0,5,13,13,14,20,20,20,15,11,11,7,7,2,0,0,1,1,1,1,1,1,1,1,0,5,13,13,14,19,19,19,14,10,10,6,6,3,0,0,1,1,1,1,1,1,1,1,0,4,7,7,8,14,14,17,13,13,13,10,10,5,3,3,0,0,0,0,0,0,0,0,0,4,7,7,8,14,14,17,13,13,13,10,10,5,3,3,0,0]', 'shiftTypes = 4', 'minStart = [5, 9, 13, 21]', 'maxStart = [8, 11, 15, 23]', 'minLength = [7, 7, 7, 7]', 'maxLength = [9, 9, 9, 9]', 'minDuties = 3', 'maxDuties = 5', 'avgMinutes = 2310', 'weightUnderCover = 1', 'weightOverCover = 1', 'weightDutiesPerWeek = 1000', 'weightShiftInstances = 60', '']
time_interval_in_Minutes = int(vars_lists[0].split(" = ")[1])
days = int(vars_lists[1].split(" = ")[1])
demand = [int(x) for x in vars_lists[2].split(" = ")[1][1:-1].split(",")]
shiftTypes = int(vars_lists[3].split(" = ")[1])
minStart = [int(x) for x in vars_lists[4].split(" = ")[1][1:-1].split(",")]
maxStart = [int(x) for x in vars_lists[5].split(" = ")[1][1:-1].split(",")]
minLength = [int(x) for x in vars_lists[6].split(" = ")[1][1:-1].split(",")]
maxLength = [int(x) for x in vars_lists[7].split(" = ")[1][1:-1].split(",")]
#minDuties = int(vars_lists[8].split(" = ")[1])
maxDuties = int(vars_lists[9].split(" = ")[1])
avgMinutes = int(vars_lists[10].split(" = ")[1])
#weightUnderCover = int(vars_lists[11].split(" = ")[1])
weightOverCover = int(vars_lists[12].split(" = ")[1])
#weightDutiesPerWeek = int(vars_lists[13].split(" = ")[1])
weightShiftInstances = int(vars_lists[14].split(" = ")[1])

# Hard constraint: Fully cover the given demand.
# Hard constraint Hard constraint: Satisfy a given minimum average shift length 
# Soft constraint: Minimize exceeding the demand
# Soft constraint: Minimize the number of different shift instances

# time_interval_in_Minutes is Slotlength for demand, minStart, maxStart, minLength, maxLength

minimumAverageShiftLength = avgMinutes/(maxDuties*time_interval_in_Minutes)

slots_per_day = int(24*60/time_interval_in_Minutes)

# Create the model.
model = cp_model.CpModel()
shifts = []

# Create the variables.
# create Possible shifts
for type in range(shiftTypes):
    for start in range(minStart[type], maxStart[type]+1):
        for length in range(minLength[type], maxLength[type]+1):
            #model.NewIntVar(0, 1, f'x_{type}_{start}_{length}')
            shifts.append((start, length))

# Assign people to shifts
# assined people to to each shift
assigned = {}
for day in range(days):
    for shift in shifts:
        #for i in range(max(demand)):
        #    assigned[(day, shift, i)] = model.NewBoolVar(f'x_{day}_{shift}_{i}')
            
        assigned[(day, shift)] = model.NewIntVar(0, max(demand), f'x_{day}_{shift}')




# Create Constraints
# Cover Demand
for day in range(days):
    for slot in range(slots_per_day):

        # shifts can go over midnight so we need to check if the shift is in the slot
        model.Add(sum([assigned[(day, shift)] for shift in shifts if ((shift[0] <= slot and shift[0] + shift[1] > slot) or (shift[0]+shift[1]-slots_per_day > slot  ))]) >= demand[day*slots_per_day + slot])

# Minimum average shift length
#model.AddDivisionEquality(sum([assigned[(day, shift)]*shift[1] for day in range(days) for shift in shifts]) / 
# sum(assigned[(day, shift)] for day in range(days) for shift in shifts)) >= minimumAverageShiftLength

#model.Add(sum(sum([assigned[(day, shift)]*shift[1] for day in range(days) for shift in shifts]) )/
#          sum(assigned[(day, shift)]) >= minimumAverageShiftLength)


# optimizer
model.Minimize(weightOverCover*sum([assigned[(day, shift)]*shift[1] for day in range(days) for shift in shifts]) +
               # Number of shift instances, not number of people assigned to shifts
               # Wrong: weightShiftInstances*sum([assigned[(day, shift)] for day in range(days) for shift in shifts]))
                weightShiftInstances*sum([assigned[(day, shift)] for day in range(days) for shift in shifts]))

#model.Minimize(sum([weightOverCover*assigned[(day, shift, i)] for day in range(days) for shift in shifts for i in range(max(demand))]))


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



