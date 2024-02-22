"""Script to find the student services workers assigned for each student based on school and name and output to a file for import into PowerSchool.

https://github.com/Philip-Greyson/D118-PS-Counselor-Population

Goes through every student in PowerSchool, checks their grade and school assignment, for high schoolers finds counselors, deans, and social workers based on last name.
For middle schoolers assignes the correct student services per building. Blanks out any inactive or elementary student.
Outputs the data to a .txt file then takes that file and uploads it to our local SFTP server in order to be imported into PowerSchool.

needs oracledb: pip install oracledb --upgrade
needs pysftp: pip install pysftp --upgrade
"""

# importing module
import datetime  # used to get current date for course info
import os  # needed to get environement variables
from datetime import *

import oracledb  # needed for connection to PowerSchool (oracle database)
import pysftp  # needed for sftp file upload

DB_UN = os.environ.get('POWERSCHOOL_READ_USER')  # username for read-only database user
DB_PW = os.environ.get('POWERSCHOOL_DB_PASSWORD')  # the password for the database account
DB_CS = os.environ.get('POWERSCHOOL_PROD_DB')  # the IP address, port, and database name to connect to

#set up sftp login info
SFTP_UN = os.environ.get('D118_SFTP_USERNAME')  # username for the d118 sftp server
SFTP_PW = os.environ.get('D118_SFTP_PASSWORD')  # password for the d118 sftp server
SFTP_HOST = os.environ.get('D118_SFTP_ADDRESS')  # ip address/URL for the d118 sftp server
CNOPTS = pysftp.CnOpts(knownhosts='known_hosts')  # connection options to use the known_hosts file for key validation

OUTPUT_FILE_NAME = 'studentServices.txt'
OUTPUT_FILE_DIRECTORY = '/sftp/studentServices/'

# store the guidance counselor names as environment variables for privacy
WHS_GUIDANCE_1 = os.environ.get('WHS_GUIDANCE_1')
WHS_GUIDANCE_2 = os.environ.get('WHS_GUIDANCE_2')
WHS_GUIDANCE_3 = os.environ.get('WHS_GUIDANCE_3')
WHS_GUIDANCE_4 = os.environ.get('WHS_GUIDANCE_4')
WHS_GUIDANCE_5 = os.environ.get('WHS_GUIDANCE_5')
WMS_GUIDANCE = os.environ.get('WMS_GUIDANCE')
MMS_GUIDANCE = os.environ.get('MMS_GUIDANCE')
WMS_PSYCH = os.environ.get('WMS_PSYCH')
MMS_PSYCH = os.environ.get('MMS_PSYCH')
WHS_PSYCH = os.environ.get('WHS_PSYCH')
WMS_SOCIAL = os.environ.get('WMS_SOCIAL')
MMS_SOCIAL = os.environ.get('MMS_SOCIAL')
WHS_SOCIAL_1 = os.environ.get('WHS_SOCIAL_1')
WHS_SOCIAL_2 = os.environ.get('WHS_SOCIAL_2')
WHS_SOCIAL_3 = os.environ.get('WHS_SOCIAL_3')
WHS_DEAN_1 = os.environ.get('WHS_DEAN_1')
WHS_DEAN_2 = os.environ.get('WHS_DEAN_2')

print(f"Database Username: {DB_UN} |Password: {DB_PW} |Server: {DB_CS}")  # debug so we can see where oracle is trying to connect to/with
print(f'SFTP Username: {SFTP_UN} | D118 SFTP Password: {SFTP_PW} | D118 SFTP Server: {SFTP_HOST}')  # debug so we can see what info sftp connection is using

if __name__ == '__main__':  # main file execution
    with open('counselor_log.txt', 'w') as log:  # open the logging file
        startTime = datetime.now()
        startTime = startTime.strftime('%H:%M:%S')
        print(f'INFO: Execution started at {startTime}')
        print(f'INFO: Execution started at {startTime}', file=log)
        with open(OUTPUT_FILE_NAME, 'w') as output:  # open the output file
            with oracledb.connect(user=DB_UN, password=DB_PW, dsn=DB_CS) as con:  # create the connecton to the database
                try:
                    with con.cursor() as cur:  # start an entry cursor
                        print(f'INFO: Connection established to PS database on version: {con.version}')
                        print(f'INFO: Connection established to PS database on version: {con.version}', file=log)

                        cur.execute('SELECT students.student_number, students.last_name, students.grade_level, students.enroll_status, students.schoolid, u_studentsuserfields.custom_counselor, u_studentsuserfields.custom_deans_house, u_def_ext_students0.custom_social, u_def_ext_students0.custom_psych\
                        FROM students LEFT JOIN u_studentsuserfields ON students.dcid = u_studentsuserfields.studentsdcid LEFT JOIN u_def_ext_students0 ON students.dcid = u_def_ext_students0.studentsdcid ORDER BY students.student_number DESC')
                        students = cur.fetchall()
                        for student in students:
                            try:
                                stuID = int(student[0])
                                last = str(student[1]).lower()
                                grade = int(student[2])
                                enroll = int(student[3])
                                school = int(student[4])
                                currentCounselor = str(student[5]) if student[5] else ''
                                currentDean = str(student[6]) if student[6] else ''
                                currentSocial = str(student[7]) if student[7] else ''
                                currentPsych = str(student[8]) if student[8] else ''
                                counselor = ''  # reset to blank for each student just in case so output does not carry over between students
                                dean = ''  # reset to blank for each student just in case so output does not carry over between students
                                social = ''  # reset to blank for each student just in case so output does not carry over between students
                                psych = ''  # reset to blank for each student just in case so output does not carry over between students
                                changed = False  # boolean to represent whether we need to include this student in the output because anything has changed
                                if grade in range(9,13) and enroll == 0:  # process high schoolers
                                    print(f'DBUG: {stuID}: {last} is in grade {grade} and active, will process as a high schooler')
                                    # print(f'DBUG: {stuID}: {last} is in grade {grade} and active, will process as a high schooler', file=log)
                                    psych = WHS_PSYCH
                                    if (last[0] < 'd'):  # A-C last names
                                        counselor = WHS_GUIDANCE_1
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        # print('DBUG: Student has name between A-C', file=log)
                                    elif (last[0] == 'd'):  # if they are D, we need to check next letter as Da-Dh is one while Di-Dz is another
                                        counselor = WHS_GUIDANCE_1 if (last[1] < 'i') else WHS_GUIDANCE_2  # check second letter
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        # print('DBUG: Student has name starting with D, finding correct counselor based on second letter - ' + last[1], file=log)
                                    elif (last[0] < 'i'):  # E-H
                                        counselor = WHS_GUIDANCE_2
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        # print('DBUG: Student has name between E-H', file=log)
                                    elif (last[0] < 'm'):  # I-L
                                        counselor = WHS_GUIDANCE_3
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_2
                                        # print('DBUG: Student has name between I-L', file=log)
                                    elif (last[0] == 'm'):  # same situation as D, M is split
                                        counselor = WHS_GUIDANCE_3 if (last[1] < 'd') else WHS_GUIDANCE_4
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_2
                                        # print('DBUG: Student has name starting with M, finding correct counselor based on second letter - ' + last[1], file=log)
                                    elif (last[0] == 'n'):  # only N, since we need I-N for social worker
                                        counselor = WHS_GUIDANCE_4
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_2
                                        # print('DBUG: Student has name starting with N', file=log)
                                    elif (last[0] < 's'):  # O-R
                                        counselor = WHS_GUIDANCE_4
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_3
                                        # print('DBUG: Student has name between O-R', file=log)
                                    elif (last[0] <= 'z'):  # S-Z
                                        counselor = WHS_GUIDANCE_5
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_3
                                        # print('DBUG: Student has name between S-Z', file=log)
                                    else:  # just in case we get through all possible
                                        counselor = 'ERROR'
                                        print('ERROR: Student last name processing failed', file=log)

                                elif (school == 1003 or school == 1004) and enroll == 0:  # if they are a middle schooler they all have the same counselor per building
                                    print(f'DBUG: {stuID}: {last} is in grade {grade} at building {school} and is active, will process as a middle schooler')
                                    # print(f'DBUG: {stuID}: {last} is in grade {grade} at building {school} and is active, will process as a middle schooler', file=log)
                                    counselor = WMS_GUIDANCE if school == 1003 else MMS_GUIDANCE
                                    dean = ''
                                    social = WMS_SOCIAL if school == 1003 else MMS_SOCIAL
                                    psych = WMS_PSYCH if school == 1003 else MMS_PSYCH
                                else:  # if they are not in 6-12 or are not active, blank out all their fields
                                    print(f'DBUG: {stuID} has a grade level of {grade} at school {school} and enroll status of {enroll}, so they will be set to blanks')
                                    # print(f'DBUG: {stuID} has a grade level of {grade} at school {school} and enroll status of {enroll}, so they will be set to blanks', file=log)
                                    counselor = ''
                                    dean = ''
                                    social = ''
                                    psych = ''
                                print(f'DBUG: {stuID} in grade {grade} at school {school}- Counselor: {counselor} | Dean: {dean} | Social Worker: {social} | Psychologist: {psych}', file=log)  # debug

                                # check to see if their counselor, dean, psychologist or social worker changed from the current value, warn if they are changing from other values and are enrolled as a sanity check
                                if counselor != currentCounselor:
                                    changed = True
                                    if enroll == 0 and currentCounselor != '':
                                        print(f'WARN: {stuID} is changing from the counselor of {currentCounselor} to {counselor}')
                                        print(f'WARN: {stuID} is changing from the counselor of {currentCounselor} to {counselor}', file=log)
                                if dean != currentDean:
                                    changed = True
                                    if enroll == 0 and currentDean != '':
                                        print(f'WARN: {stuID} is changing from the dean of {currentDean} to {dean}')
                                        print(f'WARN: {stuID} is changing from the dean of {currentDean} to {dean}', file=log)
                                if social != currentSocial:
                                    changed = True
                                    if enroll == 0 and currentSocial != '':
                                        print(f'WARN: {stuID} is changing from the social worker of {currentSocial} to {social}')
                                        print(f'WARN: {stuID} is changing from the social worker of {currentSocial} to {social}', file=log)
                                if psych != currentPsych:
                                    changed = True
                                    if enroll == 0 and currentPsych != '':
                                        print(f'WARN: {stuID} is changing from the psychologist of {currentPsych} to {psych}')
                                        print(f'WARN: {stuID} is changing from the psychologist of {currentPsych} to {psych}', file=log)

                                # do the final output to the text file only if there is change in any of the values for the student
                                if changed:
                                    print(f'{stuID}\t{counselor}\t{dean}\t{social}\t{psych}', file=output)

                            except Exception as er:
                                print(f'ERROR while processing student {student[0]}: {er}')
                                print(f'ERROR while processing student {student[0]}: {er}', file=log)

                except Exception as er:
                    print(f'ERROR while doing PowerSchool query: {er}')
                    print(f'ERROR while doing PowerSchool query: {er}', file=log)

        try:
            # Now connect to the D118 SFTP server and upload the file to be imported into PowerSchool
            with pysftp.Connection(SFTP_HOST, username=SFTP_UN, password=SFTP_PW, cnopts=CNOPTS) as sftp:
                print(f'INFO: SFTP connection to D118 at {SFTP_HOST} successfully established')
                print(f'INFO: SFTP connection to D118 at {SFTP_HOST} successfully established', file=log)
                # print(sftp.pwd)  # debug to show current directory
                # print(sftp.listdir())  # debug to show files and directories in our location
                sftp.chdir(OUTPUT_FILE_DIRECTORY)
                # print(sftp.pwd) # debug to show current directory
                # print(sftp.listdir())  # debug to show files and directories in our location
                sftp.put(OUTPUT_FILE_NAME)  # upload the file to our sftp server
                print("INFO: Student services file placed on remote server")
                print("INFO: Student services file placed on remote server", file=log)
        except Exception as er:
            print(f'ERROR while connecting to D118 SFTP server: {er}')
            print(f'ERROR while connecting to D118 SFTP server: {er}', file=log)

        endTime = datetime.now()
        endTime = endTime.strftime('%H:%M:%S')
        print(f'INFO: Execution ended at {endTime}')
        print(f'INFO: Execution ended at {endTime}', file=log)

