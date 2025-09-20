mapping = {
    1: "one",
    2: "two",
    3: "three",
    4: "four",
    5: "five",
    6: "six",
    7: "seven",
    8: "eight",
    9: "nine",
    10: "ten",
    11: "eleven",
    12: "twelve",
    13: "thirteen",
    14: "fourteen",
    15: "fifteen",
    16: "sixteen",
    17: "seventeen",
    18: "eighteen",
    19: "nineteen",
    20: "twenty",
    30: "thirty",
    40: "forty",
    50: "fifty",
    60: "sixty",
    70: "seventy",
    80: "eighty",
    90: "ninety",
}


def num_to_literal(num):
    print(num)
    output = ""
    if num / 10 >= 1:
        if num in mapping:
            return mapping[num]


        div = num // 10
        output = output + f" {mapping[div*10]}"
        num = num - (div * 10)
    if num / 1 >= 1:
        div = num // 1
        output = output + f" {mapping[div*1]}"
        num = num - (div * 1)
    return output


def test(num):
    if num == 0:
        print("zero")
    output = ""
    if num / 1000000 >= 1:
        div = num // 1000000
        output = output + f" {num_to_literal(div)} million"
        num = num - (div * 1000000)
    if num / 1000 >= 1:
        div = num // 1000
        output = output + f" {num_to_literal(div)} thousand"
        num = num - (div * 1000)
    if num / 100 >= 1:
        div = num // 100
        output = output + f" {num_to_literal(div)} hundred"
        num = num - (div * 100)
    if num / 10 >= 1:
        div = num
        output = output + f" and {num_to_literal(div)}"
        num = num - (div * 10)
    if num >= 1:
        output = output.replace("and", "")
        output = output + f" and {num_to_literal(num)}"

    print(output)


test(1000000002)
