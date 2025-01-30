def check_rebalance_values(rebalance_values):
    try:
        suma = 0
        rebalance_values = rebalance_values.split()
        for i in range(len(rebalance_values)):
            temp = rebalance_values[i].split('-')
            temp[1] = max(float(temp[1]), 0)
            rebalance_values[i] = temp
            suma += temp[1]
        if suma != 1:
            coeff = 1 / suma
        else:
            new_values = {}
            for i in range(len(rebalance_values)):
                temp = rebalance_values[i]
                new_values[temp[0]] = temp[1]
            return new_values, "ready"

        new_values = {}
        for i in range(len(rebalance_values)):
            temp = rebalance_values[i]
            temp[1] *= coeff
            if temp[1] > 0:
                new_values[temp[0]] = temp[1]
        return new_values, "rebalanced"

    except Exception as e:
        return None, "error"
