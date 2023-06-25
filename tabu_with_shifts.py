import argparse
import sys
import time
import random
import math
import copy


# initializes a solution with number nr of amployee assignments
def initialize_solution(days, shifts, nr = -1):
    assigned = {}
    shift_used = {}

    for day in range(days):
        for shift in shifts:
            assigned[(day, shift)] = 0
            shift_used[(day, shift)] = 0

    while nr > 0:
        for day in range(days):
            for shift in shifts:
                if nr > 0:
                    assigned[(day, shift)] += 1
                    shift_used[(day, shift)] = 1
                    nr -= 1

    solution = (assigned, shift_used)
    return solution


# randomly finds two shifts that are not in the tabu already
def get_random_shifts(days, shifts, tabu, tabu_flag):

    while(True):

        day = random.randint(0, days-1)
        shift = random.choice(shifts)
        day2 = random.randint(0, days-1)
        shift2 = random.choice(shifts)

        # if we do tabu then loop until we find a swap not already in the tabu
        if tabu_flag:
            if ((day, shift), (day2, shift2)) not in tabu:
                break
        else:
            break

    return day, shift, day2, shift2

def tabu_init():
    return set()

# adds nr number of employee assignments to a solution
def add_employee(new_assigned, new_shift_used, nr):

    while nr != 0:

        day = random.randint(0, days-1)
        shift = random.choice(shifts)

        if nr > 0:
            new_assigned[(day, shift)] += 1
            new_shift_used[(day, shift)] = new_assigned[(day, shift)] != 0
            nr -= 1
            #print("removed employee from ", day, " ", shift)
        else:
            if new_assigned[(day, shift)] >= 1:
                new_assigned[(day, shift)] -= 1
                new_shift_used[(day, shift)] = new_assigned[(day, shift)] != 0
                nr += 1
                #print("added employee from ", day, " ", shift)




# generates neighboring solutions
def generate_neighbor_solution(solution, days, shifts, employees, max_demand, tabu, tabu_flag = False, moves = 1):

    # we initialize the neighbor with the current solution
    (new_assigned, new_shift_used) = copy.deepcopy(solution)

    # with 5% chance we find neighbor with one extra employee assignment
    # with 5% chance we find neighbor with one less employee assignment
    if random.random() < 0.1:
        if random.random() < 0.5:
            add_employee(new_assigned, new_shift_used, 1)
            employees += 1
        else:
            add_employee(new_assigned, new_shift_used, -1)
            employees -= 1


    # otherwise we swap an employee assignment from one shift to another shift
    # we keep track of shifts that are decreased and shifts that are increased 
    # (there can be multiple of each if moves > 1)
    decrease_set = set()
    increase_set = set()
    for x in range(moves):

        # we find two random shifts that are not in the bau already
        day, shift, day2, shift2 = get_random_shifts(days, shifts, tabu, tabu_flag)

        while new_assigned[(day, shift)] <= 0:

            day, shift, day2, shift2 = get_random_shifts(days, shifts, tabu, tabu_flag)
                

        # we decrease first shift by 1
        new_assigned[(day, shift)] -= 1
        new_shift_used[(day, shift)] = new_assigned[(day, shift)] != 0
        #print("change day ", day, " shift ", shift, " : -1")

        # we increase second shift by 2
        new_assigned[(day2, shift2)] += 1
        new_shift_used[(day2, shift2)] = new_assigned[(day2, shift2)] != 0
        #print("change day ", day2, " shift ", shift2, " : +1")

        decrease_set.add((day, shift))
        increase_set.add((day2, shift2))


    # if tabu is active we add the sets of increased and decreased shifts as a pair to the tabu
    if tabu_flag:
        tabu.add((frozenset(decrease_set), frozenset(increase_set)))
        if len(tabu) % 500 == 0:
            print("tabu size = ", len(tabu))

    # we return the found neighbor
    return ((new_assigned, new_shift_used), employees)


# computes cost of a candidate solution
def compute_cost(solution, days, shifts, slots_per_day, demand, weightOverCover, weightShiftInstances):

    (assigned, shift_used) = solution

    # for each slot we calculate how many extra employees are assigned
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

    # total number of extra employee-minutes
    total_over_coverage = sum(over_coverage) * time_interval_in_Minutes
     
    # we keep track of how much is not fully covered
    under_cov = 0
    for oc in over_coverage:
        if oc < 0:
            under_cov -= oc
    # we calculate a very large penalty for under coverage
    # this ensures that satisfying the demand hard constraint is highly prioritised
    under_cov_penalty = under_cov * time_interval_in_Minutes * weightOverCover * 1000

    # we calculate total shift instances (fixed)
    total_shift_instances = 0
    for shift in shifts:
        for day in range(days):
            if shift_used[(day, shift)]:
                total_shift_instances += 1
                break

    # we calculate the average shift length in order to calculate the deficit
    total_length = sum(shift[1]*assigned[(day, shift)] for day in range(days) for shift in shifts)
    total_shifts = sum(assigned[(day, shift)] for day in range(days) for shift in shifts)
    average_shift_deficit = max((minimumAverageShiftLength - total_length / total_shifts ), 0)
    # we penalize the deficit very strongly to ensure that 
    # satisfying the average shift length hard constraint is highly prioritised
    average_shift_length_penalty = max((int(minimumAverageShiftLength * time_interval_in_Minutes) * total_shifts - total_length * time_interval_in_Minutes) * 1000, 0)

    # cost includes the penalties
    # penalties are 0 for any solution satisfying the hard constraints
    cost = weightOverCover * total_over_coverage + weightShiftInstances * total_shift_instances + under_cov_penalty + average_shift_length_penalty

    return (cost, total_over_coverage, total_shift_instances, under_cov, average_shift_deficit)

def print_assignments(days, shifts, assigned):
    for day in range(days):
        for shift in shifts:
            #print("lol")
            if assigned[(day,shift)] > 0:
                print("Assigned ", assigned[(day,shift)], "people to shift ", shift, " on day ", day)


if __name__ == "__main__":

    # we set seed for reproducibility
    # might want to remove this if stats on multiple runs are desired
    random.seed(42)

    # Create the parser
    parser = argparse.ArgumentParser()

    # Add arguments
    parser.add_argument('--file', type=str, help='The input file')
    parser.add_argument('--runtime', type=int, help='Max runtime in seconds')
    parser.add_argument('--test', action='store_true', help='A test flag - can ignore')

    # Parse arguments
    args = parser.parse_args()

    # Access arguments
    path_data = args.file
    max_runtime = args.runtime
    is_test = args.test

    if path_data is None:
        #path_data = "instances/Toys/toy3.dzn"
        #nr = 6
        #path_data = "instances/DataSet1/RandomExample3.dzn"
        #nr = 195
        #path_data = "instances/DataSet2/RandomExample5.dzn"
        #nr = 141
        #path_data = "instances/DataSet1/RandomExample4.dzn"
        #path_data = "instances/DataSet2/RandomExample28.dzn"
        path_data = "instances/DataSet2/RandomExample30.dzn"

    with open(path_data) as f:
        data = f.read()

    # maximum runtime of the optimization
    if max_runtime is None:
        # we run it for 10 minutes
        # in practice due to implementation issues no better solutions are found after about 120 seconds
        max_runtime = 600


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

    # neighborhood_distance can be defined to decide how far we search for a solution


    minimumAverageShiftLength = avgMinutes / (maxDuties * time_interval_in_Minutes)
    slots_per_day = int(24 * 60 / time_interval_in_Minutes)
    max_demand = max(demand)


    print("minimumAverageShiftLength = ",minimumAverageShiftLength)
    print("slots_per_day = ",slots_per_day)


    # create Possible shifts
    total_shift_length = 0
    total_possible_shifts = 0
    shifts = []
    for type in range(shiftTypes):
        for start in range(minStart[type], maxStart[type]+1):
            for length in range(minLength[type], maxLength[type]+1):
                shifts.append((start, length))
                total_possible_shifts += 1
                total_shift_length += length

    # we calculate the average length for all possible shifts
    average_theoretical_shift_length = total_shift_length / total_possible_shifts
    # to calculate a reasonable number of initial employee assignments
    employees = math.floor(sum(demand) / average_theoretical_shift_length)
    print("employees = ", employees)
    # we initialize the first solution
    solution = initialize_solution(days, shifts, employees)
    (ass, sh) = solution
    print_assignments(days, shifts, ass)

    # we calculate initial cost and associated values
    (cost, total_over_coverage, total_shift_instances, under_cov, average_shift_deficit) = compute_cost(solution, days, shifts, slots_per_day, demand, weightOverCover, weightShiftInstances)

    # experimental
    annealing = False

    # tabu active
    tabu_flag = True
    tabu = tabu_init()
    tabu_too_large_ct = 0
    max_tabu_size = 5000
    print("tabu size = ", len(tabu))
    stime = time.time()
    time_last_change = stime
    # be begin looking at neighbors with a single employee swap
    moves = 1

    # Loop many times
    loop = 0
    iter_since_last_cost_decrease = 0
    while loop < 1000000:
        loop +=1
        iter_since_last_cost_decrease += 1
        rtime = time.time() - stime

        if loop % 1000 == 0:
            print("runtime: ", rtime)

        # Generate a new solution by making a small random change
        (new_solution, new_employees) = generate_neighbor_solution(solution, days, shifts, employees, max_demand, tabu, tabu_flag, moves)

        # if tabu too large we reset it to avoid bugs
        # with better tuning future versions could have no tabu reset for better performance
        if len(tabu) >= max_tabu_size:
            tabu_too_large_ct += 1
            print("tabu size = ", len(tabu))
            print("tabu size too big")
            print("tabu_too_large_ct = ", tabu_too_large_ct)
            tabu = tabu_init()
            print("tabu size = ", len(tabu))

        if tabu_too_large_ct >= 5:
            print("tabu_too_large_ct = ", tabu_too_large_ct)
            moves += 1
            print("moves = ", moves)
            tabu_too_large_ct = 0


        # Calculate the cost of the new solution
        (new_cost, new_total_over_coverage, new_total_shift_instances, new_under_cov, new_average_shift_deficit) = compute_cost(new_solution, days, shifts, slots_per_day, demand, weightOverCover, weightShiftInstances)

        # Calculate the change in cost
        delta_cost = new_cost - cost

        # If the new solution is better, accept it
        if delta_cost < 0:
            print("delta cost = ", delta_cost)
            employees = new_employees
            print("employees = ", employees)
            # reset tabu list on finding better solution
            # future versions might find ways to keep parts of the tabu
            print("tabu size = ", len(tabu))
            print("reset tabu")
            tabu = tabu_init()
            tabu_too_large_ct = 0
            iter_since_last_cost_decrease = 0
            solution = new_solution
            cost = new_cost
            total_over_coverage = new_total_over_coverage
            total_shift_instances = new_total_shift_instances
            under_cov = new_under_cov
            average_shift_deficit = new_average_shift_deficit
            print("new cost = ", cost)
            print("time since last change: ", time.time() - time_last_change)
            time_last_change = time.time()
            print("Total over coverage: ", total_over_coverage)
            print("Total shift instances: ", total_shift_instances)
            print("under coverage: ", under_cov)
            print("average shift deficit: ", average_shift_deficit * 100 / minimumAverageShiftLength, "%")
            (ass, sh) = solution
            print_assignments(days, shifts, ass)
        else:
            # annealing inspired - experimental
            # If the new solution is worse, accept it with a probability that depends on when the last improvement was found
            if annealing == True:
                #probability = math.exp(-delta_cost / temperature)
                #print("probability = ", probability)
                probability = max(iter_since_last_cost_decrease / 10000, 0.1)
                if random.random() < probability:
                    print("annealed")
                    solution = new_solution
                    cost = new_cost
                    total_over_coverage = new_total_over_coverage
                    total_shift_instances = new_total_shift_instances
                    print("new cost = ", cost)

        if time.time() - stime > max_runtime:
            print("time is up")
            break


    (assigned, shift_used) = solution
    # Return the best solution found
    print("Results for ", path_data)
    print("Final cost: ", cost)
    print("Total over coverage: ", total_over_coverage)
    print("Total shift instances: ", total_shift_instances)
    print_assignments(days, shifts, assigned)


