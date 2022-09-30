# importing module
import oracledb  # needed for connection to PowerSchool (oracle database)
import sys  # needed for non scrolling text output
import os  # needed to get environment variables
import pysftp  # needed for sftp file upload

un = 'PSNavigator'  # PSNavigator is read only, PS is read/write and should not be used unless really neccessary
# the password for the PSNavigator account
pw = os.environ.get('POWERSCHOOL_DB_PASSWORD')
# the IP address, port, and database name to connect to
cs = os.environ.get('POWERSCHOOL_PROD_DB')

#set up sftp login info
sftpUN = os.environ.get('D118_SFTP_USERNAME')
sftpPW = os.environ.get('D118_SFTP_PASSWORD')
sftpHOST = os.environ.get('D118_SFTP_ADDRESS')
# connection options to use the known_hosts file for key validation
cnopts = pysftp.CnOpts(knownhosts='known_hosts')

# store the guidance counselor names as environment variables for privacy
hs1 = os.environ.get('WHS_GUIDANCE_1')
hs2 = os.environ.get('WHS_GUIDANCE_2')
hs3 = os.environ.get('WHS_GUIDANCE_3')
hs4 = os.environ.get('WHS_GUIDANCE_4')
hs5 = os.environ.get('WHS_GUIDANCE_5')
wms = os.environ.get('WMS_GUIDANCE')
mms = os.environ.get('MMS_GUIDANCE')


# debug so we can see where oracle is trying to connect to/with
print("Username: " + str(un) + " |Password: " + str(pw) + " |Server: " + str(cs))
# debug so we can see what sftp credentials are being used
print("SFTP Username: " + str(sftpUN) + " |SFTP Password: " + str(sftpPW) + " |SFTP Server: " + str(sftpHOST))  

# create the connecton to the database
with oracledb.connect(user=un, password=pw, dsn=cs) as con:
    with con.cursor() as cur:  # start an entry cursor
        with open('counselor_log.txt', 'w') as outputLog:  # open the logging file
            with open('counselors.txt', 'w') as output:  # open the output file
                print("Connection established: " + con.version)
                print("Connection established: " + con.version, file=outputLog)

                cur.execute('SELECT students.student_number, students.last_name, students.grade_level, students.enroll_status, u_studentsuserfields.custom_counselor, students.schoolid FROM students LEFT JOIN u_studentsuserfields ON students.dcid = u_studentsuserfields.studentsdcid ORDER BY students.grade_level DESC')
                rows = cur.fetchall()
                for count, student in enumerate(rows):
                    try:
                        # sort of fancy text to display progress of how many students are being processed without making newlines
                        sys.stdout.write('\rProccessing student entry %i' % count)
                        sys.stdout.flush()
                        # print('\n' + str(student[0])) # debug
                        stuID = int(student[0])
                        last = str(student[1]).lower()
                        grade = int(student[2])
                        enroll = int(student[3])
                        currentCounselor = str(student[4]) if student[4] else ''
                        school = int(student[5])
                        if (grade > 8 and grade < 13) and enroll == 0:
                            print(str(stuID) + ': ' + last + ' is in grade ' + str(grade) + ' and active, will process', file=outputLog) # debug

                            if (last[0] < 'd'):  # A-C last names
                                counselor = hs1
                                print('Student has name between A-C', file=outputLog)
                            elif (last[0] == 'd'):  # if they are D, we need to check next letter as Da-Dh is one while Di-Dz is another
                                counselor = hs1 if (last[1] < 'i') else hs2  # check second letter
                                print('Student has name starting with D, finding correct counselor based on second letter - ' + last[1], file=outputLog)
                            elif (last[0] < 'i'):  # E-H
                                counselor = hs2
                                print('Student has name between E-H', file=outputLog)
                            elif (last[0] < 'm'):  # I-L
                                counselor = hs3
                                print('Student has name between I-L', file=outputLog)
                            elif (last[0] == 'm'):  # same situation as D, M is split
                                counselor = hs3 if (last[1] < 'd') else hs4
                                print('Student has name starting with M, finding correct counselor based on second letter - ' + last[1], file=outputLog)
                            elif (last[0] < 's'):  # N-R
                                counselor = hs4
                                print('Student has name between N-R', file=outputLog)
                            elif (last[0] <= 'z'):  # S-Z
                                counselor = hs5
                                print('Student has name between S-Z', file=outputLog)
                            else:  # just in case we get through all possible
                                counselor = 'ERROR'
                                print('ERROR: Student last name processing failed', file=outputLog)

                            print(str(stuID) + ': ' + counselor, file=outputLog)
                        elif (school == 1003 or school == 1004) and enroll == 0: # if they are a middle schooler they all have the same counselor per building
                            print(str(stuID) + ': ' + last + ' is in grade ' + str(grade) + ' at building ' + str(school) + ' and active, will process', file=outputLog) # debug
                            counselor = wms if school == 1003 else mms
                            print(str(stuID) + ': ' + counselor, file=outputLog)
                        else:
                            print(str(stuID) + ' has a grade level of ' + str(grade) + ' at school ' + str(school) + ' and enroll of ' + str(enroll) + ' so they will be set to blank', file=outputLog)
                            counselor = ''
                        if enroll == 0 and (counselor != currentCounselor and currentCounselor != ''):
                            print(str(stuID) + ': Difference in current vs new counselor:' + currentCounselor + ' vs ' + counselor, file=outputLog)
                        print(str(stuID) + '\t' + counselor, file=output)
                    except Exception as er:
                        print('Error on ' + str(student[0]) + ': ' + str(er))
                        
            print('') # spacer line
            with pysftp.Connection(sftpHOST, username=sftpUN, password=sftpPW, cnopts=cnopts) as sftp:
                print('SFTP connection established')
                print('SFTP connection established', file=outputLog)
                # print(sftp.pwd)  # debug to show current directory
                # print(sftp.listdir())  # debug to show files and directories in our location
                sftp.chdir('/sftp/counselors/')
                # print(sftp.pwd) # debug to show current directory
                # print(sftp.listdir())  # debug to show files and directories in our location
                sftp.put('counselors.txt') #upload the file onto the sftp server
                print("Counselor file placed on remote server for")
                print("Counselor file placed on remote server", file=outputLog)

