#!/usr/bin/env python3
# -*- coding: utf-8 -*-

'''
Скрипт для удаления бэкапов через api
'''

import sys
import re
import json
import os
import argparse
import bareos.bsock
import subprocess


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def bareos_connect( dir_pass ):
    print("ESTABLISH CONNECT TO BAREOS")
    try:
        password = bareos.bsock.Password(dir_pass)
        directorconsole = bareos.bsock.DirectorConsoleJson(address=bareos_dir_host,
                                                           port=9101,
                                                           password=password)
    except:
        print(f"WE CAN NOT CONNECT TO BAREOS DIRECTOR: {directorconsole}")
    return directorconsole


def yes_no_dialog(default_answer="no"):
    answers = {"yes":1, "y":1, "ye":1,
               "no":0, "n":0}
    question = f"{bcolors.WARNING}Do you wanna delete jobs?{bcolors.ENDC}"
    tip = " [y/N] "
    while True:
        print( question + tip + ": ")
        user_answer = input().lower()
        if default_answer is not None and user_answer == '':
            return answers[default_answer]
        elif user_answer in answers:
            return answers[user_answer]
        else:
            print("Please enter yes/y or no/nn")


def check_jobid_exist(client_jobs, jobid):
    status = False
    for job in client_jobs:
        if job['jobid'] == jobid:
            status = True
    return status


def print_client_jobs( jobs ):
    print(f"{'jobid':<10} {'client':<25} {'starttime':<20} {'level':<15} {'jobstatus':<15}")
    for job in jobs:
        # set human ready job level
        job_level = job['level']
        if job_level == 'I':
            job_level = 'Incremental'
        if job_level == 'F':
            job_level = 'Full'
        # set human ready job status
        job_status = job['jobstatus']
        if job_status == 'f':
            job_status = 'Fatal'
        if job_status == 'T':
            job_status = 'Ok'
        if job_status == 'W':
            job_status = 'Warning (non fatal)'
        if job_status == 'E':
            job_status = 'Terminated in Error'
        # print
        print(f"{job['jobid']:<10} {job['client']:<25} {job['starttime']:<20} {job_level:<15} {job_status:<15}")


def get_jobs_list_for_delete( client_jobs_for_delete ):
    result =[]
    for job in client_jobs_for_delete:
        result.append(job['jobid'])
    return result


def get_volumes_jobid(jobs_list_for_delete):
    result = []
    for jobid in jobs_list_for_delete:
        volumes = directorconsole.call(f"list volumes jobid={jobid}")
        if volumes['volumes']:
            result.append(volumes['volumes'][0]['volumename'])
    return result


def get_client_jobs( client, jobid=None ):
    result = []
    client_jobs = directorconsole.call(f"list jobs client={client}")
    for job in client_jobs['jobs']:
        result.append(job)
        if job['jobid'] != None and job['jobid'] == jobid:
            break
    return result


def delete_volumes_files(volumes, client):

    for volume in volumes:
        volume_path = bareos_sd_storage + '/' + client + '/' + volume
        print(f"Deleting volume file {volume_path} from {bareos_sd_host}")
        delete_cmd = "sudo rm " + volume_path
        subprocess.Popen(f"ssh {bareos_sd_host} {delete_cmd}", shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()


def delete_volumes(volumes):
    for volume in volumes:
        print(f'delete volume {volume} from bareos catalog')
        directorconsole.call(f"delete volume={volume}")


def delete_jobs(jobs):
    for job in jobs:
        print(f'delete {job} from bareos catalog')
        directorconsole.call(f"delete jobid={job}")


def delete_client_jobs( client ):
    # get all client jobs
    client_jobs = get_client_jobs( client )
    # print client jobs
    print_client_jobs( client_jobs )
    # select jobid
    jobid = input( f"{bcolors.OKGREEN}Please enter jobid, all jobes before jobid will be deleted\n enter: {bcolors.ENDC}" )
    if jobid == '':
        print( f"{bcolors.FAIL}Enter valid jobid{bcolors.ENDC}" )
        exit(0)
    # check jobid exist for client
    jobid_exist = check_jobid_exist( client_jobs, jobid )
    if not jobid_exist:
        print( f"{bcolors.FAIL}{client} does not contain jobid {jobid}{bcolors.ENDC}" )
        exit(0)
    # list jobs for delete
    client_jobs_for_delete = get_client_jobs( client, jobid )
    print_client_jobs( client_jobs_for_delete )
    print( f"{bcolors.WARNING}Above jobs wil be deleted{bcolors.ENDC}" )
    # delete with aprove
    delete_aprove = yes_no_dialog()
    if delete_aprove == 1:
        jobs_list_for_delete = get_jobs_list_for_delete( client_jobs_for_delete )
        volumes = get_volumes_jobid(jobs_list_for_delete)
        if volumes:
            delete_volumes_files(volumes, client)
            delete_volumes(volumes)
        if jobs_list_for_delete:
            delete_jobs(jobs_list_for_delete)
        # get current client jobs
        client_jobs = get_client_jobs( client )
        # print current client jobs
        print(f"{bcolors.OKGREEN} Current Jobs{bcolors.ENDC}")
        print_client_jobs( client_jobs )
    else:
        print("Oh pussy cat...")


if __name__ == '__main__':

    bareos_dir_host = ''
    bareos_sd_host = ''
    bareos_sd_storage = ''

    parser = argparse.ArgumentParser()
    parser.add_argument("--password", help="bareos dir pass", metavar="pass")
    parser.add_argument("--client", help="restore data", metavar="client")
    parser.add_argument("--delete", help="restore data", action="store_true")

    args = parser.parse_args()

    directorconsole = bareos_connect(args.password)

    if args.client and args.delete:
        delete_client_jobs( args.client )

    exit(0)
