# D118-PS-Counselor-Population

Script to find the correct student services employees for each student, then output that to a .txt file for upload into PowerSchool custom fields.

## Overview

The script is pretty simple and not particularly elegant in its format. It simply does a query for all students in PowerSchool, gets their current student service staff fields: counselor, dean, social worker, and psychologist. Then each student is iterated through one at a time. Students who are active and in high school are processed by last name in a series of if/elif statements to find the correct staff for each name. Middle school students are processed based on building number and given the correct student services staff for their buildings. Inactive and elementary students are given an empty string for each field. The script will warn if any of the fields for active students are changing as a sanity check, and then output the values for any students who have had a change in staff (to reduce the overall size of the output file and the time it takes PowerSchool to import it).

## Requirements

The following Environment Variables must be set on the machine running the script:

- POWERSCHOOL_READ_USER
- POWERSCHOOL_DB_PASSWORD
- POWERSCHOOL_PROD_DB
- D118_SFTP_USERNAME
- D118_SFTP_PASSWORD
- D118_SFTP_ADDRESS

These are fairly self explanatory, and just relate to the usernames, passwords, and host IP/URLs for PowerSchool and the local SFTP server. If you wish to directly edit the script and include these credentials, you can.

Additionally, the following Python libraries must be installed on the host machine (links to the installation guide):

- [Python-oracledb](https://python-oracledb.readthedocs.io/en/latest/user_guide/installation.html)
- [pysftp](https://pypi.org/project/pysftp/)

**As part of the pysftp connection to the output SFTP server, you must include the server host key in a file** with no extension named "known_hosts" in the same directory as the Python script. You can see [here](https://pysftp.readthedocs.io/en/release_0.2.9/cookbook.html#pysftp-cnopts) for details on how it is used, but the easiest way to include this I have found is to create an SSH connection from a linux machine using the login info and then find the key (the newest entry should be on the bottom) in ~/.ssh/known_hosts and copy and paste that into a new file named "known_hosts" in the script directory.

You will also need a SFTP server running and accessible that is able to have files written to it in the directory /sftp/studentServices/ or you will need to customize the script (see below). That setup is a bit out of the scope of this readme.
In order to import the information into PowerSchool, a scheduled AutoComm job should be setup, that uses the managed connection to your SFTP server, and imports into student_number, and whichever custom fields for the student services information you have set up, using tab as a field delimiter, LF as the record delimiter with the UTF-8 character set. It is important to note that the order of the AutoComm fields must match the order of the output which is defined by the line `print(f'{stuID}\t{counselor}\t{dean}\t{social}\t{psych}', file=output)` which uses their student number, counselor, dean, social worker, then psychologist as the default order.

## Customization

This is a pretty specific basic script for our district, and is likely going to be very different for other use cases but might be useful as an overall outline/template for customization. Some things you will want to change:

- All the staff names are stored as environment variables specific to our schools. You will need to change these or hardcode the names into the places they are assigned to output the correct staff names.
- Filtering the high school section (where students have different staff based on last name) is done by grade levels `in range(9-13)` which is our grade 9-12 since we only have one high school. If you have different grade levels or multiple buildings you will need to change this range or add another check for school number.
  - Additionally, the last name breakpoints are specific to our district where some letters are split into two sections such as Da-Dh being one counselor and Di-Dz being another. You will need to change these around to suit your needs.
- The middle school filtering (where every student has the same staff per building) just checks the schoolid numbers against our two middle schools, this will need to be changed to match your buildings.
- `OUTPUT_FILE_NAME` and `OUTPUT_FILE_DIRECTORY`define the file name and directory on the SFTP server that the file will be exported to. These combined will make up the path for the AutoComm import.
- We reference the custom fields that hold the student services staff info in our SQL query to get their current values in order to compare against what it should be as it runs. These are: `u_studentsuserfields.custom_counselor, u_studentsuserfields.custom_deans_house, u_def_ext_students0.custom_social, u_def_ext_students0.custom_psych`. You will need to change these to match the fields you use to store this information, which will match the AutoComm import settings.
