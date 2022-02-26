def filter_number(df_to_filter, inputs):
    if inputs[0] == "<":
        val_filter = df_to_filter[inputs[1]] < inputs[2]
        return df_to_filter[val_filter]
    elif inputs[0] == ">":
        val_filter = df_to_filter[inputs[1]] > inputs[2]
        return df_to_filter[val_filter]
    elif inputs[0] == ">=":
        val_filter = df_to_filter[inputs[1]] >= inputs[2]
        return df_to_filter[val_filter]
    elif inputs[0] == "<=":
        val_filter = df_to_filter[inputs[1]] < inputs[2]
        return df_to_filter[val_filter]
    elif inputs[0] == "between":
        val_filter1 = df_to_filter[inputs[1]] < inputs[2][1]
        val_filter2 = df_to_filter[inputs[1]] > inputs[2][0]
        return df_to_filter[val_filter1 & val_filter2]
    else:
        return "Error invalid values for filter"


def filter_name(df_to_filter, inputs):
    return df_to_filter[df_to_filter[inputs[0]].isin(inputs[1])]
