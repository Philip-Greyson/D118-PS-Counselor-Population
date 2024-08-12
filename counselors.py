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
WHS_GUIDANCE_1_EMAIL = os.environ.get('WHS_GUIDANCE_1_EMAIL')
WHS_GUIDANCE_2 = os.environ.get('WHS_GUIDANCE_2')
WHS_GUIDANCE_2_EMAIL = os.environ.get('WHS_GUIDANCE_2_EMAIL')
WHS_GUIDANCE_3 = os.environ.get('WHS_GUIDANCE_3')
WHS_GUIDANCE_3_EMAIL = os.environ.get('WHS_GUIDANCE_3_EMAIL')
WHS_GUIDANCE_4 = os.environ.get('WHS_GUIDANCE_4')
WHS_GUIDANCE_4_EMAIL = os.environ.get('WHS_GUIDANCE_4_EMAIL')
WHS_GUIDANCE_5 = os.environ.get('WHS_GUIDANCE_5')
WHS_GUIDANCE_5_EMAIL = os.environ.get('WHS_GUIDANCE_5_EMAIL')
WHS_GUIDANCE_ACADEMY = os.environ.get('WHS_GUIDANCE_ACADEMY')
WHS_GUIDANCE_ACADEMY_EMAIL = os.environ.get('WHS_GUIDANCE_ACADEMY_EMAIL')
WMS_GUIDANCE = os.environ.get('WMS_GUIDANCE')
WMS_GUIDANCE_EMAIL = os.environ.get('WMS_GUIDANCE_EMAIL')
MMS_GUIDANCE = os.environ.get('MMS_GUIDANCE')
MMS_GUIDANCE_EMAIL = os.environ.get('MMS_GUIDANCE_EMAIL')
WMS_PSYCH = os.environ.get('WMS_PSYCH')
MMS_PSYCH = os.environ.get('MMS_PSYCH')
WHS_PSYCH_1 = os.environ.get('WHS_PSYCH_1')
WHS_PSYCH_2 = os.environ.get('WHS_PSYCH_2')
WMS_SOCIAL = os.environ.get('WMS_SOCIAL')
MMS_SOCIAL = os.environ.get('MMS_SOCIAL')
WHS_SOCIAL_1 = os.environ.get('WHS_SOCIAL_1')
WHS_SOCIAL_2 = os.environ.get('WHS_SOCIAL_2')
WHS_SOCIAL_3 = os.environ.get('WHS_SOCIAL_3')
WHS_SOCIAL_ACADEMY = os.environ.get('WHS_SOCIAL_ACADEMY')
WHS_SOCIAL_ILS = os.environ.get('WHS_SOCIAL_ILS')
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

                        cur.execute('SELECT stu.student_number, stu.last_name, stu.grade_level, stu.enroll_status, stu.schoolid, stufields.custom_counselor, stufields.custom_deans_house, stuext.custom_social, stuext.custom_psych, stufields.custom_counselor_email, stuext.academy, stuext.ils\
                        FROM students stu LEFT JOIN u_studentsuserfields stufields ON stu.dcid = stufields.studentsdcid LEFT JOIN u_def_ext_students0 stuext ON stu.dcid = stuext.studentsdcid ORDER BY stu.student_number DESC')
                        students = cur.fetchall()
                        for student in students:
                            try:
                                stuID = int(student[0])
                                last = str(student[1]).lower()
                                grade = int(student[2])
                                enroll = int(student[3])
                                school = int(student[4])
                                currentCounselor = str(student[5]) if student[5] else ''
                                currentCounselorEmail = str(student[9]) if student[9] else ''
                                currentDean = str(student[6]) if student[6] else ''
                                currentSocial = str(student[7]) if student[7] else ''
                                currentPsych = str(student[8]) if student[8] else ''
                                isAcademy = True if student[10] == 1 else False
                                isILS = True if student[11] == 1 else False
                                counselor = ''  # reset to blank for each student just in case so output does not carry over between students
                                counselorEmail = ''  # reset to blank for each student just in case so output does not carry over between students
                                dean = ''  # reset to blank for each student just in case so output does not carry over between students
                                social = ''  # reset to blank for each student just in case so output does not carry over between students
                                psych = ''  # reset to blank for each student just in case so output does not carry over between students
                                changed = False  # boolean to represent whether we need to include this student in the output because anything has changed
                                if grade in range(9,13) and enroll == 0:  # process high schoolers
                                    print(f'DBUG: {stuID}: {last} is in grade {grade} and active, will process as a high schooler')
                                    # print(f'DBUG: {stuID}: {last} is in grade {grade} and active, will process as a high schooler', file=log)
                                    if (last[0] == 'a'): # A last names
                                        counselor = WHS_GUIDANCE_1
                                        counselorEmail = WHS_GUIDANCE_1_EMAIL
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        psych = WHS_PSYCH_1
                                        # print('DBUG: Student has a last name starting with A', file=log)
                                    elif (last[0] < 'g'): # B-F
                                        counselor = WHS_GUIDANCE_2
                                        counselorEmail = WHS_GUIDANCE_2_EMAIL
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        psych = WHS_PSYCH_1
                                        # print('DBUG: Student has a last name between B-F', file=log)
                                    elif (last[0] == 'g'):  # if they are D, we need to check next letter as Da-Dh is one while Di-Dz is another
                                        counselor = WHS_GUIDANCE_2 if (last[1] == 'a') else WHS_GUIDANCE_3  # check second letter
                                        counselorEmail = WHS_GUIDANCE_2_EMAIL if (last[1] == 'a') else WHS_GUIDANCE_3_EMAIL  # check second letter
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        psych = WHS_PSYCH_1
                                        # print('DBUG: Student has name starting with G, finding correct counselor based on second letter - ' + last[1], file=log)
                                    elif (last[0] < 'm'):  # H-L
                                        counselor = WHS_GUIDANCE_3
                                        counselorEmail = WHS_GUIDANCE_3_EMAIL
                                        dean = WHS_DEAN_1
                                        social = WHS_SOCIAL_1
                                        psych = WHS_PSYCH_1
                                        # print('DBUG: Student has name between H-L', file=log)
                                    elif (last[0] < 'r'):  # M-Q
                                        counselor = WHS_GUIDANCE_4
                                        counselorEmail = WHS_GUIDANCE_4_EMAIL
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_2
                                        psych = WHS_PSYCH_2
                                        # print('DBUG: Student has name between M-Q', file=log)
                                    elif (last[0] == 'r'):  # same situation as G, R is split
                                        counselor = WHS_GUIDANCE_4 if (last[1] < 'j') else WHS_GUIDANCE_5
                                        counselorEmail = WHS_GUIDANCE_4_EMAIL if (last[1] < 'j') else WHS_GUIDANCE_5_EMAIL
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_2
                                        psych = WHS_PSYCH_2
                                        # print('DBUG: Student has name starting with R, finding correct counselor based on second letter - ' + last[1], file=log)
                                    elif (last[0] <= 'z'):  # S-Z
                                        counselor = WHS_GUIDANCE_5
                                        counselorEmail = WHS_GUIDANCE_5_EMAIL
                                        dean = WHS_DEAN_2
                                        social = WHS_SOCIAL_2
                                        psych = WHS_PSYCH_2
                                        # print('DBUG: Student has name between S-Z', file=log)
                                    else:  # just in case we get through all possible
                                        counselor = 'ERROR'
                                        print('ERROR: Student last name processing failed', file=log)

                                    # do an override for academy and ILS students
                                    if isAcademy:
                                        counselor = WHS_GUIDANCE_ACADEMY
                                        counselorEmail = WHS_GUIDANCE_ACADEMY_EMAIL
                                        social = WHS_SOCIAL_ACADEMY
                                        print('DBUG: Student is an academy student, overriding their counselor and social worker', file=log)
                                    if isILS:
                                        social = WHS_SOCIAL_ILS
                                        print('DBUG: Student is an ILS student, overriding their social worker', file=log)

                                elif (school == 1003 or school == 1004) and enroll == 0:  # if they are a middle schooler they all have the same counselor per building
                                    print(f'DBUG: {stuID}: {last} is in grade {grade} at building {school} and is active, will process as a middle schooler')
                                    # print(f'DBUG: {stuID}: {last} is in grade {grade} at building {school} and is active, will process as a middle schooler', file=log)
                                    counselor = WMS_GUIDANCE if school == 1003 else MMS_GUIDANCE
                                    counselorEmail = WMS_GUIDANCE_EMAIL if school == 1003 else MMS_GUIDANCE_EMAIL
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
                                print(f'DBUG: {stuID} in grade {grade} at school {school}- Counselor: {counselor}: {counselorEmail} | Dean: {dean} | Social Worker: {social} | Psychologist: {psych}', file=log)  # debug

                                # check to see if their counselor, dean, psychologist or social worker changed from the current value, warn if they are changing from other values and are enrolled as a sanity check
                                if counselor != currentCounselor:
                                    changed = True
                                    if enroll == 0 and currentCounselor != '':
                                        print(f'WARN: {stuID} is changing from the counselor of {currentCounselor} to {counselor}')
                                        print(f'WARN: {stuID} is changing from the counselor of {currentCounselor} to {counselor}', file=log)
                                if counselorEmail != currentCounselorEmail:
                                    changed = True
                                    if enroll == 0 and currentCounselorEmail != '':
                                        print(f'WARN: {stuID} is changing from the counselor email of {currentCounselorEmail} to {counselorEmail}')
                                        print(f'WARN: {stuID} is changing from the counselor email of {currentCounselorEmail} to {counselorEmail}', file=log)
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
                                    print(f'{stuID}\t{counselor}\t{dean}\t{social}\t{psych}\t{counselorEmail}', file=output)

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
