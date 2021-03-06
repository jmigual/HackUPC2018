#!/usr/bin/env python3
import argparse
import requests
import datetime
from typing import List, Tuple, Dict


def get_token():
    with open("token.key") as f:
        return f.readline().replace("\n", "")


API_URL = 'https://api.fib.upc.edu/v2/'
TOKEN = get_token()


def ranges_to_score(ranges: List[List[Tuple[int, int]]], mornings: bool) -> int:
    empty_days = 0
    score = 0
    for day in ranges:
        if len(day) <= 0:
            empty_days += 1

        last = None
        for r_start, r_end in day:
            day_score = r_end - r_start
            if not mornings:
                day_score = 60*24 - day_score

            score += day_score
            if last is not None:
                score += 4*(r_start - last)
            last = r_end
    return score


def convert_to_ranges(timetable: Dict[str, int], courses: dict) -> List[List[Tuple[int, int]]]:
    total = []
    for course_key, course_group in timetable.items():
        group_num = course_group // 10
        subgroup_num = course_group % 10
        total += courses[course_key][group_num]["time"]

        if subgroup_num != 0:
            total += courses[course_key][group_num]["subgroups"][subgroup_num]

    total_days: List[List[Tuple[int, int]]] = [[] for _ in range(7)]

    for r_start, r_end in total:
        day = r_start // (60*24)
        r_start -= day*60*24
        r_end -= day*60*24
        total_days[day].append((r_start, r_end))
    for day in total_days:
        day.sort(key=lambda x: x[0])
    return total_days


def get_scores(timetables: List[Dict[str, int]], courses: dict, mornings: bool) -> List[Tuple[Dict[str, int], int]]:
    result = []
    for timetable in timetables:
        ranges = convert_to_ranges(timetable, courses)
        score = ranges_to_score(ranges, mornings)
        result.append((timetable, score))
    result.sort(key=lambda x: x[1])
    return result


def overlaps(ranges: List[Tuple[int, int]], new_ranges: List[Tuple[int, int]]) -> bool:
    for start, end in ranges:
        for n_start, n_end in new_ranges:
            if start <= n_start < end or start < n_end <= end:
                return True
    return False


def get_timetables(courses: dict, ranges: List[Tuple[int, int]], groups: dict) -> List[Dict[str, int]]:
    if len(courses) <= 0:
        return [groups]

    result = []
    courses_copy = courses.copy()
    subject_key, subject_data = courses_copy.popitem()
    for group_key, group_data in subject_data.items():
        group_time = group_data["time"]
        if overlaps(ranges, group_time):
            continue
        new_ranges = ranges + group_time

        if len(group_data["subgroups"]) <= 0:
            result += get_timetables(courses_copy, new_ranges, {**groups, subject_key: group_key*10})
        else:
            for subgroup_key, subgroup_data in group_data["subgroups"].items():
                if overlaps(new_ranges, subgroup_data):
                    continue
                result += get_timetables(courses_copy, new_ranges + subgroup_data,
                                         {**groups, subject_key: (group_key*10 + subgroup_key)})

    return result


def time_to_int(time: str) -> int:
    h, m = time.split(":")
    return int(h)*60 + int(m)


def build_database(data: dict) -> dict:
    subjects_data = {}
    # Parse the JSON file
    for d in data:
        code = d['codi_assig']
        groups = subjects_data.get(code, {})

        t_start = int(d["dia_setmana"])*60*24 + time_to_int(d["inici"])
        t_end = t_start + int(d["durada"])*60

        total_num = int(d["grup"])
        group_num = total_num // 10
        subgroup_num = total_num % 10
        group = groups.get(group_num, {
            "subgroups": {},
            "time": []
        })

        if total_num % 10 == 0:
            group["time"].append((t_start, t_end))
        else:
            subgroup = group["subgroups"].get(subgroup_num, [])
            subgroup.append((t_start, t_end))
            group["subgroups"][subgroup_num] = subgroup
        groups[group_num] = group
        subjects_data[code] = groups

    return subjects_data


def get_timetable(semester: str, courses: List[str], mornings: bool) -> Dict[str, int]:
    date_str = f"{semester}"
    res = requests.get(f"{API_URL}quadrimestres/{date_str}/classes/",
                       params={
                           "format": "json",
                           "codi_assig": courses,
                           "client_id": TOKEN
                       })
    print(res.request.path_url)
    data = res.json()
    if data["count"] <= 0:
        print(f"No data received, instead {data}")

    database = build_database(data["results"])
    timetables = get_timetables(database, [], {})
    scores = get_scores(timetables, database, mornings)
    print(len(timetables))
    if len(scores) > 0:
        return scores[0][0]
    return {}


def get_available_courses(semester: str) -> List[str]:
    date_str = f"{semester}"
    res = requests.get(f"{API_URL}quadrimestres/{date_str}/assignatures",
                       params={
                           "format": "json",
                           "client_id": TOKEN
                       })
    print(res.request.path_url)
    return res.json()["results"]


def timetable_to_url(timetable: Dict[str, int]) -> str:
    base_url = "https://www.fib.upc.edu/ca/estudis/graus/grau-en-enginyeria-informatica/horaris?class=true"
    for key, value in timetable.items():
        group = value - (value % 10)
        base_url += f"&a={key}_{value}&a={key}_{group}"

    return base_url


def get_semesters() -> List[str]:
    year = datetime.datetime.now().year
    return [f"{year}Q1", f"{year}Q2"]



def main(args: dict):
    get_available_courses(2018, 1)
    get_timetable(2018, 1, ["F", "FM", "IC", "PRO1"], True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    arguments, _ = parser.parse_known_args()
    main(vars(arguments))

