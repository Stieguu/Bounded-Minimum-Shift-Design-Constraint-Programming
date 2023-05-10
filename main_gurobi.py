import gurobipy as gp
from gurobipy import GRB
import argparse
import sys
import time

# Create the parser
parser = argparse.ArgumentParser()

# Add arguments
parser.add_argument('--file', type=str, help='The input file')

# Parse arguments
args = parser.parse_args()

# Access arguments
path_data = args.file

if path_data is None:
    path_data = "instances/toy1.dzn"

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



# create Possible shifts
shifts = []
for type in range(shiftTypes):
    for start in range(minStart[type], maxStart[type]+1):
        for length in range(minLength[type], maxLength[type]+1):
            shifts.append((start, length))


with gp.Env() as env, gp.Model(env=env) as model:
    try:
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
                assigned[(day, shift)] = model.addVar(vtype=GRB.INTEGER, name=f'assigned_{day}_{shift}')
                # whether the shift has been assigned to at least one employee
                shift_used[(day, shift)] = model.addVar(vtype=GRB.BINARY, name=f'shift_used_{day}_{shift}')
                model.addConstr(assigned[(day, shift)] >= shift_used[(day, shift)])
                model.addConstr(assigned[(day, shift)] <= shift_used[(day, shift)] * max_demand)


        total_length = model.addVar(vtype=GRB.INTEGER, name='total_length')
        model.addConstr(sum(shift[1]*assigned[(day, shift)] for day in range(days) for shift in shifts) == total_length)

        total_shifts = model.addVar(vtype=GRB.INTEGER, name='total_shifts')
        model.addConstr(sum(assigned[(day, shift)] for day in range(days) for shift in shifts) == total_shifts)

        model.addConstr(total_length * time_interval_in_Minutes >= int(minimumAverageShiftLength * time_interval_in_Minutes) * total_shifts)


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
                over_coverage.append(model.addVar(vtype=GRB.INTEGER, name=f'over_coverage_{day}_{slot}'))
                # we set the over_coverage variables to be the number of extra employees at slot
                model.addConstr(shifts_today + shifts_yesterday - demand[day*slots_per_day + slot] == over_coverage[-1])
                # we add constraint that this must be at least 0, i.e. demand is met at slot
                model.addConstr(over_coverage[-1] >= 0)


        # sum of the over_coverage for all slots
        total_over_coverage = model.addVar(vtype=GRB.INTEGER, name="total_over_coverage")
        model.addConstr(total_over_coverage == sum(over_coverage) * time_interval_in_Minutes)

        # total shift instances
        total_shift_instances = model.addVar(vtype=GRB.INTEGER, name="total_shift_instances")
        model.addConstr(total_shift_instances == sum(shift_used.values()))


        obj = gp.LinExpr(0)
        obj.add(total_over_coverage, weightOverCover)
        obj.add(total_shift_instances, weightShiftInstances)
        model.setObjective(obj, sense=GRB.MINIMIZE)


        model.update()

        # write model to file in readable format (useful for debugging)
        model.write("model.lp")

        # Set a time limit of 10 minutes
        model.setParam('TimeLimit', 600)

        stime = time.perf_counter()
        model.optimize()
        rtime = time.perf_counter() - stime

        sys.stderr.write(f"Finished processing {path_data} in {rtime}\n")
        if model.status == gp.GRB.OPTIMAL:
            sys.stderr.write("status optimal\n")
            sys.stderr.write(f"objective =  {model.ObjVal}\n")
            print(f"objective =  {model.ObjVal}")
            print('total_over_coverage = ', model.getVarByName('total_over_coverage').x)
            print('total_shift_instances = ', model.getVarByName('total_shift_instances').x)
            for day in range(days):
                for shift in shifts:
                    if model.getVarByName(f'assigned_{day}_{shift}').x > 0:
                        var_name = f'assigned_{day}_{shift}'
                        print(f'Assigned {model.getVarByName(var_name).x} people to shift {shift} on day {day}')
        elif model.status == gp.GRB.INFEASIBLE:
            sys.stderr.write("status infeasible\n")
        elif model.status == gp.GRB.TIME_LIMIT:
            sys.stderr.write("status time limit reached\n")
            sys.stderr.write(f"objective =  {model.ObjVal}\n")
            print(f"objective =  {model.ObjVal}")
            print('total_over_coverage = ', model.getVarByName('total_over_coverage').x)
            print('total_shift_instances = ', model.getVarByName('total_shift_instances').x)
            for day in range(days):
                for shift in shifts:
                    var_name = f'assigned_{day}_{shift}'
                    if model.getVarByName(f'assigned_{day}_{shift}').x > 0:
                        print(f'Assigned {model.getVarByName(var_name).x} people to shift {shift} on day {day}')


        print(f"obj {round(model.ObjVal)}")
        print(f"time {model.Runtime:.3f} s")

    except gp.GurobiError as e:
        print(f"Error code {e.errno}: {e}")
    except AttributeError as e:
        print("Encountered an attribute error")
        print(e)