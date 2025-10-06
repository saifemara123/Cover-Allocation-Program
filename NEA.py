# Import required libraries
import tkinter as tk # Importing the tkinter library for GUI
import tkcalendar as tkc
import calendar
import datetime
import sqlite3 # Importing sqlite3 for database interactions
import re
import random
import yagmail
import os
import string
from tkinter import messagebox
from tkinter import ttk
from tkinter import simpledialog # Importing specific components from tkinter
from tkinter.simpledialog import askstring
from tkinter import *
from time import strftime
from PIL import Image, ImageTk # Importing PIL for image handling

class MyTimetableApp:
    """Main application class for managing the GUI."""

    def __init__(self, root):
        """Initialize the main application window."""
        self.root = root
        self.root.title("My.Timetable")
        self.root.geometry('800x400')
        self.root.resizable(False, False)

        self.current_user = None
        self.current_role = None

        self.allocated = False

        today = datetime.datetime.now()

        try:
            """Tries to open the file and sets it to False if empty"""
            f = open('state.txt', 'r')
            value = f.read().strip()
            if not value:
                value = "False"
            self.Cleared = value
            f.close()
        except FileNotFoundError:
            """Creates the file and sets the default state to False"""
            f = open("AbsenceLog.txt", "a")
            f.close()
            self.Cleared = "False"

        if self.Cleared == "False" and today.day == 1:
            """Clears Current Covers and sets state to cleared"""

            teachers = database.get_all_usernames()
            for teacher in teachers:
                database.reset_current_covers(teacher)

            self.Cleared = "True"
            f = open('state.txt', 'w')
            f.write(self.Cleared)
            f.close()

        elif today.day != 1:
            self.Cleared = "False"
            f = open('state.txt', 'w')
            f.write(self.Cleared)
            f.close()

        # Create a container frame
        self.container = tk.Frame(root)
        
        self.container.pack(fill="both", expand=True)

        #initializes empty dictionary to store frame instances 
        self.frames = {}
        for F in (MainMenu, Admin_Choice, RegisterScreen, LoginScreen, SLTScreen, TeacherScreen, AbsenceScreen,
                   SLTAbsenceScreen, MarkDaysAbsent, SLTMarkDaysAbsent, AbsenceConfirmation,
                     SLTAbsenceConfirmation, AddTeacherScreen, AccessDatabaseScreen,
                       ViewDatabaseScreen, EditDatabaseScreen, DeleteDatabaseScreen,
                         AdminViewDatabase, AdminEditDatabase):
            
            frame = F(parent=self.container, controller=self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="news")
        
        self.allocated = False
        self.reverted = False

        self.root.protocol("WM_DELETE_WINDOW", self.window_close)

        self.root.after(10000, self.check_time)  # Check every 10 seconds

        self.show_frame(MainMenu)  # Start with the main menu

    def show_frame(self, frame_class):
        #Raise a frame to the front for display.
        frame = self.frames[frame_class]
        frame.tkraise()
        
        # Ensure timetable refreshes when switching to SLT or Teacher screen
        if isinstance(frame, SLTScreen) or isinstance(frame, TeacherScreen):
            self.update_all_timelines()
    
    # Creates a function to ensure the user returns to the approporiate screen based on role
    def go_back(self):
        if self.current_role == "SLT":
            self.show_frame(SLTScreen)
        elif self.current_role =="Admin":
            self.show_frame(Admin_Choice)
        else:
            self.show_frame(TeacherScreen)
    
    # Creates a function that sets button colors on leave and enter events
    def binder(self, button):
        button.bind("<Enter>", lambda e: self.on_enter(button, "#cacaca"))
        button.bind("<Leave>", lambda e: self.on_leave(button, "SystemButtonFace"))

    def on_enter(self, button, backcolour):
        button.config(background=backcolour)
    
    def on_leave(self, button, backcolour):
        button.config(background=backcolour)

    # Ensures all screens and data base viewing tables are updating as it gets called
    def update_all_timelines(self):
        """Refreshes the timetable for both SLT and Normal Teacher screens."""
        if isinstance(self.frames[SLTScreen], SLTScreen):
            self.frames[SLTScreen].timetable.update_timetable()
    
        if isinstance(self.frames[TeacherScreen], TeacherScreen):
            self.frames[TeacherScreen].timetable.update_timetable()
        
        self.frames[AccessDatabaseScreen].update_treeview() 
        self.frames[ViewDatabaseScreen].update_labels()
        self.frames[AdminViewDatabase].update_labels()   
        self.frames[SLTAbsenceConfirmation].update_absent_teachers()

    # Closes the program
    def window_close(self):
        self.root.destroy()
        database.delete_absence()

    def check_time(self):
        #Check the time periodically and run cover allocation and reverts the allocations at the right time.
        now = datetime.datetime.now()

        # Allocate covers between 6:30 and 7:00 AM if not already allocated
        if now.hour == 6 and now.minute >= 30 and not self.allocated:
            M = MainAlgorithm(self)
            M.cover_allocation()
            self.allocated = True  # Prevent re-running allocation

        # Reset allocation flag after 3 PM to allow next day's allocation
        if (now.hour >= 15 and not self.reverted) or (now.hour < 6 and not self.reverted):
            M = MainAlgorithm(self)
            self.reverted = True
            self.allocated = False  # Reset for next day
            M.revert_covers()

        # Use Tkinter’s after() to call itself again in 10 seconds
        self.root.after(10000, self.check_time)  # Check again in 10 seconds

class Database:
    """Class for managing database interactions for the application"""

    def __init__(self):
            """Initialize the database and creates necessary tables."""
            connection = sqlite3.connect('MyTimetable.db') # Establish a connection to the SQLite database
            cursor = connection.cursor() # Create a cursor object to execute SQL commands

            # Create Teachers table if it does not exist to ensure a new table isn't created at run everytime
            cursor.execute("""CREATE TABLE IF NOT EXISTS Teachers (
                Username TEXT PRIMARY KEY,
                Fullname TEXT,
                Role TEXT,
                Subject_Department TEXT,
                Current_Covers INTEGER,
                Cover_Limit INTEGER
                )""")
            
            #Table creation for the 5 das of the week
            cursor.execute("""CREATE TABLE IF NOT EXISTS MondayLessons (
                Username TEXT,
                Lesson_Number INTEGER,
                Subject TEXT,
                Class TEXT,
                Substitute TEXT,
                PRIMARY KEY (Username, Lesson_Number),
                FOREIGN KEY (Username) REFERENCES Teachers(Username)
                )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS TuesdayLessons (
                Username TEXT,
                Lesson_Number INTEGER,
                Subject TEXT,
                Class TEXT,
                Substitute TEXT,
                PRIMARY KEY (Username, Lesson_Number),
                FOREIGN KEY (Username) REFERENCES Teachers(Username)
                )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS WednesdayLessons (
                Username TEXT,
                Lesson_Number INTEGER,
                Subject TEXT,
                Class TEXT,
                Substitute TEXT,
                PRIMARY KEY (Username, Lesson_Number),
                FOREIGN KEY (Username) REFERENCES Teachers(Username)
                )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS ThursdayLessons (
                Username TEXT,
                Lesson_Number INTEGER,
                Subject TEXT,
                Class TEXT,
                Substitute TEXT,
                PRIMARY KEY (Username, Lesson_Number),
                FOREIGN KEY (Username) REFERENCES Teachers(Username)
                )""")

            cursor.execute("""CREATE TABLE IF NOT EXISTS FridayLessons (
                Username TEXT,
                Lesson_Number INTEGER,
                Subject TEXT,
                Class TEXT,
                Substitute TEXT,
                PRIMARY KEY (Username, Lesson_Number),
                FOREIGN KEY (Username) REFERENCES Teachers(Username)
                )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS AbsenceLog (
                Username TEXT,
                Date TEXT,
                Reason TEXT,
                PRIMARY KEY (Username, Date)
                )""")
            
            cursor.execute("""CREATE TABLE IF NOT EXISTS Hashing (
                Username TEXT,
                Salt TEXT,
                Hash_Value TEXT,
                PRIMARY KEY (Username)
                )""")
            
            # Inserts values into the teacher, hashing, and weekday tables for testing purposes
            cursor.execute("""INSERT OR IGNORE INTO Teachers VALUES ("a", "It Worked", "SLT", "Mathematics", 0, 11)""")
            cursor.execute("""INSERT OR IGNORE INTO Hashing VALUES ("a", "rxaax85xc2Oxe8xb5xf4xa29xe0txacx19xf1q", "2156371292")""")

            cursor.executemany("""INSERT OR IGNORE INTO MondayLessons VALUES (?, ?, ?, ?, ?)""", [
                ("a", 1, "Maths", "11J", "None"),
                ("a", 2, "Free", " ", " "),
                ("a", 3, "Free", " ", " "),
                ("a", 4, "Free", " ", " "),
                ("a", 5, "Free", " ", " "),
                ("a", 6, "CS", "COL3", "None"),
                ("a", 7, "CS", "COL3", "None")
            ])

            # Insert Tuesday lessons
            cursor.executemany("""INSERT OR IGNORE INTO TuesdayLessons VALUES (?, ?, ?, ?, ?)""", [
                ("a", 1, "Maths", "11J", "None"),
                ("a", 2, "BUS", "10G", "None"),
                ("a", 3, "Free", " ", " "),
                ("a", 4, "Free", " ", " "),
                ("a", 5, "Free", " ", " "),
                ("a", 6, "CS", "COL3", "None"),
                ("a", 7, "Free", " ", " ")
            ])

            # Insert Wednesday lessons
            cursor.executemany("""INSERT OR IGNORE INTO WednesdayLessons VALUES (?, ?, ?, ?, ?)""", [
                ("a", 1, "BUS", "10G", "None"),
                ("a", 2, "Free", " ", " "),
                ("a", 3, "Free", " ", " "),
                ("a", 4, "Maths", "11J", "None"),
                ("a", 5, "Free", " ", " "),
                ("a", 6, "BUS", "10G", "None"),
                ("a", 7, "Maths", "11J", "None")
            ])

            # Insert Thursday lessons
            cursor.executemany("""INSERT OR IGNORE INTO ThursdayLessons VALUES (?, ?, ?, ?, ?)""", [
                ("a", 1, "Free", " ", " "),
                ("a", 2, "BUS", "10G", "None"),
                ("a", 3, "BUS", "10G", "None"),
                ("a", 4, "BUS", "10G", "None"),
                ("a", 5, "CS", "COL3", "None"),
                ("a", 6, "CS", "COL3", "None"),
                ("a", 7, "Maths", "11J", "None")
            ])

            # Insert Friday lessons
            cursor.executemany("""INSERT OR IGNORE INTO FridayLessons VALUES (?, ?, ?, ?, ?)""", [
                ("a", 1, "Maths", "11J", "None"),
                ("a", 2, "CS", "COL3", "None"),
                ("a", 3, "Free", " ", " "),
                ("a", 4, "Free", " ", " "),
                ("a", 5, "Free", " ", " ")
            ])

            connection.commit()
            connection.close()
    
    def add_teacher(self, username, fullname, role, subject_department, current_covers, cover_limit):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Inserts teacher data
        cursor.execute("""INSERT INTO Teachers VALUES (?, ?, ?, ?, ?, ?)""", (username, fullname, role, subject_department, current_covers, cover_limit))
        connection.commit()
        connection.close()

    def get_fullname(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Selects the fullname that matches the inputed username in the teachers table
        cursor.execute("""SELECT Fullname FROM Teachers WHERE Username = ?""", (username,))
        fullname = cursor.fetchone()
        connection.close()
        return fullname[0] if fullname else None # Returns the fullname or none if not found

    def get_role(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Selects the role that is saved under the inputed username in the teachers table
        cursor.execute("""SELECT Role FROM Teachers WHERE Username = ?""", (username,))
        role = cursor.fetchone()
        connection.close()
        return role[0] if role else None # Returns the role or none if not found

    def get_subject_department(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Selects the department that is saved under the inputed username in the teachers table
        cursor.execute("""SELECT Subject_Department FROM Teachers WHERE Username = ?""", (username,))
        subject_department = cursor.fetchone()
        connection.close()
        return subject_department[0] if subject_department else None # Return subject department or None if not found
    
    def get_cover_limit(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Selects the cover limit that is saved under the inputed username in the teachers table
        cursor.execute("""SELECT Cover_Limit FROM Teachers WHERE Username = ?""", (username,))
        cover_limit = cursor.fetchone()
        connection.close()
        return cover_limit[0] if cover_limit else None # Return the cover limit or None if not found

    def get_current_covers(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        cursor.execute("""SELECT Current_Covers FROM Teachers WHERE Username = ?""", (username,))
        current_covers = cursor.fetchone()
        connection.close()
        return current_covers[0] if current_covers else None # Return the current covers or None if not found

    def increment_current_covers(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        current_covers = database.get_current_covers(username) # Gets the current covers
        current_covers = current_covers + 1 # Increases/Increments the current covers by 1
        cursor.execute("""UPDATE Teachers SET Current_Covers = ? WHERE Username = ?""", (current_covers, username)) # Updates the system with the new value
        
        connection.commit()
        connection.close()
    
    def reset_current_covers(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        current_covers = database.get_current_covers(username)
        current_covers = 0
        cursor.execute("""UPDATE Teachers SET Current_Covers = ? WHERE Username = ?""", (current_covers, username)) # Resets current covers to 0
        
        connection.commit()
        connection.close()

    def add_lesson(self, username, day, lesson_number, subject, class_name, substitute):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Insert lesson into the appropriate day's table
        if day == "Monday":
            cursor.execute("""INSERT INTO MondayLessons (Username, Lesson_Number, Subject, Class, Substitute) VALUES (?, ?, ?, ?, ?)""", (username, lesson_number, subject, class_name, substitute))
        elif day == "Tuesday":
            cursor.execute("""INSERT INTO TuesdayLessons (Username, Lesson_Number, Subject, Class, Substitute) VALUES (?, ?, ?, ?, ?)""", (username, lesson_number, subject, class_name, substitute))
        elif day == "Wednesday":
            cursor.execute("""INSERT INTO WednesdayLessons (Username, Lesson_Number, Subject, Class, Substitute) VALUES (?, ?, ?, ?, ?)""", (username, lesson_number, subject, class_name, substitute))
        elif day == "Thursday":
            cursor.execute("""INSERT INTO ThursdayLessons (Username, Lesson_Number, Subject, Class, Substitute) VALUES (?, ?, ?, ?, ?)""", (username, lesson_number, subject, class_name, substitute))
        elif day == "Friday":
            cursor.execute("""INSERT INTO FridayLessons (Username, Lesson_Number, Subject, Class, Substitute) VALUES (?, ?, ?, ?, ?)""", (username, lesson_number, subject, class_name, substitute))

        connection.commit()
        connection.close()

    def edit_lesson(self, username, day, lesson_number, subject, class_name, substitute):
        """Edit an existing lesson for a teacher"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Updates lesson in the appropriate day's table
        if day == "Monday":
            cursor.execute("""UPDATE MondayLessons SET Subject = ?, Class = ?, Substitute = ? WHERE Username = ? AND Lesson_Number = ?""", (subject, class_name, substitute, username, lesson_number))
        elif day == "Tuesday":
            cursor.execute("""UPDATE TuesdayLessons SET Subject = ?, Class = ?, Substitute = ? WHERE Username = ? AND Lesson_Number = ?""", (subject, class_name, substitute, username, lesson_number))
        elif day == "Wednesday":
            cursor.execute("""UPDATE WednesdayLessons SET Subject = ?, Class = ?, Substitute = ? WHERE Username = ? AND Lesson_Number = ?""", (subject, class_name, substitute, username, lesson_number))
        elif day == "Thursday":
            cursor.execute("""UPDATE ThursdayLessons SET Subject = ?, Class = ?, Substitute = ? WHERE Username = ? AND Lesson_Number = ?""", (subject, class_name, substitute, username, lesson_number))
        elif day == "Friday":
            cursor.execute("""UPDATE FridayLessons SET Subject = ?, Class = ?, Substitute = ? WHERE Username = ? AND Lesson_Number = ?""", (subject, class_name, substitute, username, lesson_number))

        connection.commit()
        connection.close()

    def get_all_teachers(self):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()
        cursor.execute("""SELECT * FROM Teachers""") # Query for all teachers
        teachers = cursor.fetchall() # Fetches all the results
        connection.close()

        return teachers # Returns the list of teachers
    
    def get_all_usernames(self):
        """Retrieves all usernames rom the Teachers table"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()
        cursor.execute("""SELECT Username FROM Teachers""") # Query for all usernames
        usernames = cursor.fetchall()
        connection.close()

        return usernames #Returns the list of usernames

    def get_all_lessons(self, username, day):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()
        lessons = [] # Initializes an empty list to contain lessons
        
        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Query based on inputed day of the week
        if day == "Monday":
            cursor.execute("""SELECT * FROM MondayLessons WHERE Username = ?""", (username,))
        elif day == "Tuesday":
            cursor.execute("""SELECT * FROM TuesdayLessons WHERE Username = ?""", (username,))
        elif day == "Wednesday":
            cursor.execute("""SELECT * FROM WednesdayLessons WHERE Username = ?""", (username,))
        elif day == "Thursday":
            cursor.execute("""SELECT * FROM ThursdayLessons WHERE Username = ?""", (username,))
        elif day == "Friday":
            cursor.execute("""SELECT * FROM FridayLessons WHERE Username = ?""", (username,))

        lessons = cursor.fetchall() # Fetches all results
        connection.close()
        return lessons # Returns the list of lessons

    def get_one_lesson(self, username, day, lesson_num):
        """Retrieves a specific lesson for a teacher on a specific day"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()
        
        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        cursor.execute(f"""SELECT * FROM {day}Lessons WHERE Username = ? AND Lesson_Number =?""", (username, lesson_num))

        lesson = cursor.fetchone()
        connection.close()

        return lesson # Return the lesson details
    
    def delete_teacher_user(self, username):
        """Delete a teacher from the database based on their username"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        cursor.execute("""DELETE FROM Teachers WHERE Username = ?""", (username,)) # Delete the teacher's record and details from the system

        connection.commit()
        connection.close()

    def delete_teacher_data(self, username):
        """Delete all lesson data for a teacher based on their username"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Delete lessons for each day of the week
        cursor.execute("""DELETE FROM MondayLessons WHERE Username = ?""", (username,))
        cursor.execute("""DELETE FROM TuesdayLessons WHERE Username = ?""", (username,))
        cursor.execute("""DELETE FROM WednesdayLessons WHERE Username = ?""", (username,))
        cursor.execute("""DELETE FROM ThursdayLessons WHERE Username = ?""", (username,))
        cursor.execute("""DELETE FROM FridayLessons WHERE Username = ?""", (username,))

        connection.commit()
        connection.close()

    def add_absence(self, username, date, reason):
        """Logs an absence of a teacher"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        date_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime.date) else date # Formats data into an appropriate format

        cursor.execute("""INSERT INTO AbsenceLog (Username, Date, Reason) VALUES (?, ?, ?)""", (username, date_str, reason)) # Logs the absence in the databasse
        connection.commit()
        connection.close()

    def delete_absence(self):
        """Delete absence records for all teachers for the current date (Only for testing purposes)"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        teachers = self.get_all_usernames() # Gets all the usernames
        date = datetime.datetime.now().strftime('%Y-%m-%d') # Gets today's date

        for teacher in teachers:
            teacher = teacher[0] # Extract username from list 
            cursor.execute("""DELETE FROM AbsenceLog WHERE Username = ? and Date = ?""", (teacher, date)) # Deletes the absence

        connection.commit()
        connection.close()

    def is_absent(self, username, date):
        """Check if a teacher is absent on a specific date"""
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        date_str = date.strftime("%Y-%m-%d") if isinstance(date, datetime.date) else date # Formats date

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        cursor.execute("""SELECT * FROM AbsenceLog WHERE Username = ? AND Date = ?""", (username, date_str)) # Checks if a record of the absence is present
        return True if cursor.fetchone() is not None else False # Returns True if the teacher is absent, otherwise returns False

    def generate_salt(self):
        """Generate a random 16 byte salt for password hashing"""
        length = 16 # Length of the salt
        salt = os.urandom(length) # Generate random bytes
        salt = str(salt) # Converts them to string format
        return salt # Returns the generated salt

    def hashing_algorithm(self, password, salt): # Use of hashing
        """Hashes a password using a custom algorithm with the provided salt"""
        hash_value = 0 # Initializes the hash value variable
        
        combined = salt + password # Combines the salt and password 
        for _ in range(100): # Performs the process 100 iterations for safety purposes
            for char in combined:
                hash_value += ord(char) # Adds the ASCII values
                hash_value = (hash_value * 31) ^ (hash_value >> 16) # Hashing operation
                hash_value = hash_value % (2**32) # Ensures hash value fits in 32 bits making sure its a limited size
            
            combined = salt + str(hash_value) # Updates the combined value for the next iteration
        
        return hash_value # Returns the final hash value

    def store_password(self, username, password):
        salt = self.generate_salt() # Generates a salt
        hash_value = self.hashing_algorithm(password, salt) # Hashes the password without ever saving it

        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        #Stores the hash value and generated salt under the username in the hashing table
        cursor.execute("""INSERT INTO Hashing (Username, Salt, Hash_Value) VALUES (?, ?, ?)""", (username, salt, hash_value))
        connection.commit()
        connection.close()
    
    def delete_password(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        cursor.execute("""DELETE FROM Hashing WHERE Username = ?""",(username,)) # Delete all hashing/password details from the system
        connection.commit()
        connection.close()

    def get_hash(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        # Query for hash value based on username
        cursor.execute("""SELECT Hash_Value FROM Hashing WHERE Username = ?""", (username,))
        hash = cursor.fetchone()
        connection.close()
        return hash[0] if hash else None # Returns hash value or None if not found

    def get_salt(self, username):
        connection = sqlite3.connect('MyTimetable.db')
        cursor = connection.cursor()

        if isinstance(username, tuple):
            username = username[0] # Extracts the username if it's a tuple

        #Query for salt
        cursor.execute("""SELECT Salt FROM Hashing WHERE Username = ?""", (username,))
        salt = cursor.fetchone()
        connection.close()
        return salt[0] if salt else None # Returns salt or None if not found

    def verify_password(self, username, password):
        stored_hash = str(self.get_hash(username)) # Gets the stored hash value in the database
        salt = self.get_salt(username) # Gets the stored salt in the database

        current_hash = str(self.hashing_algorithm(password, salt)) # Runs the hashing algorithm on the newly entered password

        if current_hash == stored_hash: # Checks that the entered password generates the same hash as the saved password
            return True # Thus returns True since password hashes match
        else:
            return False # Return false since password don't match

class MainMenu(tk.Frame):
    """Main Menu Screen."""

    def __init__(self, parent, controller):
        """Initializes the MainMenu class"""
        #calling the constructor of a parent from a child (sub-class)
        super().__init__(parent) # Use of OOP with inheritance
        self.controller = controller # Store the reference to the main application controller

        # Creates a label for the title
        tk.Label(self, text="My TimeTable", font=("Cooper Black", 50)).pack(padx=175,pady=20) # Use of meaningful identifier names

        # Create buttons for navigation to other screens
        register = tk.Button(self, text="Register", font=("Times", 14), width=20, height=3, relief="groove", 
                  command=lambda: controller.show_frame(RegisterScreen)) # Modularization of code
        register.pack(pady=10) # Adds the button with padding to determine location on screen

        login = tk.Button(self, text="Login", font=("Times", 14), width=20, height=3, relief="groove", 
                  command=lambda: controller.show_frame(LoginScreen))
        login.pack(pady=10)
        
        exit = tk.Button(self, text="Exit", font=("Times", 10), width=20, height=3, bg="tomato", relief="groove", 
                  command=lambda: controller.window_close()) # Use of local variables
        exit.pack(pady=10)

        admin = tk.Button(self, text="ONLY ADMIN ACCESS", font=("Futurama, 8"), width=20, height=2, bg="darkblue", relief="groove", fg="white",
                  command=lambda: self.admin()) 
        admin.place(x=0, y=0) # Positioning the admin button using place in this case the top left corner of the screen

        # Binds the hover effects for buttons
        self.binder(register) # Binds hover effects to the register button
        self.binder(login) # Binds hover effects to the login button
        exit.bind("<Enter>", lambda e: self.on_enter(exit, "#e20000", "black")) # Change color of the button on hover
        exit.bind("<Leave>", lambda e: self.on_leave(exit, "tomato", "black")) # Reset color on leave
        admin.bind("<Enter>", lambda e: self.on_enter(admin, "#0047de", "white"))
        admin.bind("<Leave>", lambda e: self.on_leave(admin, "darkblue", "white"))

        # Loads images for the logo and watermark to customize main menu screen
        self.logo = ImageTk.PhotoImage(Image.open(r"C:\Users\Administrator\Desktop\Logo.png")) # Use of image handling
        self.watermark = ImageTk.PhotoImage(Image.open(r"C:\Users\Administrator\Desktop\Watermark.png"))

        # Places the images on the screen
        Label(self, image=self.logo).place(x=50, y=120)
        Label(self, image=self.watermark).place(x=550, y=120)

    def admin(self):
        """Prompts the user for an admin password"""
        protection = askstring("","Password Protected!\nEnter Admin Password:",show="*") # Use of User-defined algorithms

        if protection is None:
            return # Exits smoothly if no input is provided

        if protection == "11235813": # Checks for the correct admind password
            self.controller.current_role = 'Admin' # Sets user tole to Admin allowing special permissions
            self.controller.show_frame(Admin_Choice) # Raises the admin choice screen
        else:
            messagebox.showerror("Error", "Wrong Password\nEntry Denied!") # Use of Exception Handling

    def binder(self, button):
        """Binds hover effects to buttons"""
        button.bind("<Enter>", lambda e: self.on_enter(button, "#cacaca", "black")) # Change background on hover
        button.bind("<Leave>", lambda e: self.on_leave(button, "SystemButtonFace", "black")) # Reset background on leave

    def on_enter(self, button, backcolour, textcolour):
        """Handles mouse enter event to change button appearance"""
        button.config(background=backcolour, foreground=textcolour) # Changes button background and text color on hover 
    
    def on_leave(self, button, backcolour, textcolour):
        """Handle mouse leave event to reset button appearance"""
        button.config(background=backcolour, foreground=textcolour) # Reset button background and text color

class Admin_Choice(tk.Frame):
    """Admin Choice Screen for managing and editing admin exclusive variables"""

    def __init__(self, parent, controller):
        """Initialize the AdminChoice class"""
        super().__init__(parent) # Use of OOP with inheritance
        self.controller = controller

        # Create buttons for various admin tasks
        add = tk.Button(self, text="Add Teacher", width=30, height=4, relief="groove",
                  command=lambda: self.controller.show_frame(AddTeacherScreen)) # Raises the AddTeacher Screen
        add.place(x=485, y=120)
        
        access = tk.Button(self, text="Access Database", width=30, height=4, relief="groove",
                  command=lambda: self.controller.show_frame(AccessDatabaseScreen)) # Raises the AccessDatabase Screen
        access.place(x=100, y=120)
        
        exitadmin = tk.Button(self, text="Exit Admin Mode", width=25, height=2, relief="groove",
                  command=lambda: self.leave_admin()) # Exits admin mode and returns to the main menu
        exitadmin.place(x=310, y=200)

        controller.binder(add)
        controller.binder(access)
        controller.binder(exitadmin)
    
    def leave_admin(self):
        """Handles exiting admin mode and returning to the main menu"""
        self.controller.current_role = None # Resets the current role to None so that permissions are stripped
        self.controller.show_frame(MainMenu) # Raises the MainMenu screen

class RegisterScreen(tk.Frame):
    """Registration Screen for new users to create an account"""

    def __init__(self, parent, controller):
        """Initializes the RegisterScreen class"""
        super().__init__(parent)
        self.controller = controller

        # Creates labels and entry fields for user registration
        tk.Label(self, text="Fullname:", font=("Times", 14)).grid(row=0, column=1, padx=160, pady=10, sticky="w")
        self.fullname = tk.Entry(self, width=50)
        self.fullname.grid(row=0, column=1, padx=250, pady=10)

        tk.Label(self, text="Username:", font=("Times", 14)).grid(row=1, column=1, padx=160, pady=10, sticky="w")
        self.username = tk.Entry(self, width=50)
        self.username.grid(row=1, column=1, padx=250, pady=10)

        tk.Label(self, text="Password:", font=("Times", 14)).grid(row=2, column=1, padx=160, pady=10, sticky="w")
        self.password = tk.Entry(self, show="*", width=50)
        self.password.grid(row=2, column=1, padx=250, pady=10)

        tk.Label(self, text="Repeat Password:", font=("Times", 14)).grid(row=3, column=1, padx=103.5, pady=10, sticky="w")
        self.repeated_password = tk.Entry(self, show="*", width=50)
        self.repeated_password.grid(row=3, column=1, padx=250, pady=10)

        # Creates buttons for registration and cancel
        register = tk.Button(self, text="Register", width=20, height=2, relief="groove", 
                  command=lambda: self.register_user())
        register.grid(row=5, column=1, pady=20)

        cancel = tk.Button(self, text="Cancel", width=20, height=2, relief="groove", 
                  command=lambda: self.clear_entries())
        cancel.grid(row=6, column=1, pady=10)

        # Bind hover effectos for buttons
        controller.binder(register)
        controller.binder(cancel)

    def register_user(self):
        """Handle user registration""" # Use of OOP Encapsulation
        # Gets and formats the variables
        fullname = self.fullname.get().strip().title()
        username = self.username.get().strip().lower()
        password = self.password.get().strip()
        repeat_password = self.repeated_password.get().strip()

        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday"]
        
        #check if all fields are filled
        if not fullname or not username or not password:
            messagebox.showerror("Error", "All fields are required!") # Use of Exception Handling
            return #Returns if validation fails

        if len(fullname.split()) <= 1:
            messagebox.showerror("Error", "Fullname must include atleast first and last name!")
            return

        #check if passwords match
        if password != repeat_password:
            messagebox.showerror("Error", "Passwords do not match!")
            return
        
        #check if username ends with "_gfs"
        if not username.endswith("_gfs"):
            messagebox.showerror("Error", "Username must end with '_gfs'!")
            return
        
        if not re.match(r"^(?!.*\..*\..*)[A-Za-z0-9]+(\.[A-Za-z0-9]+)?$", username.replace("_gfs","")):
            messagebox.showerror("Error", "Start of Username must only include alphanumeric characters and one fullstop")
            return

        if not username[0].isalpha():
            messagebox.showerror("Error", "Username must start with a letter!")
            return
        
        #check if username already exists
        if database.get_fullname(username):
            messagebox.showerror("Error", "Username already exists!")
            return
                
        #checks that the password does not contain any spaces
        if " " in password:
            messagebox.showerror("Error", "Password must not contain spaces!")
            return
        
        #Regular Expression checks that the password contains at least 8 characters, one uppercase letter, one lowercase letter, one digit, and one special character
        if not re.match(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?_&])[A-Za-z\d@$!%*?_&].{8,}$", password):
            messagebox.showerror("Error", "Password must contain at least 9 characters, one uppercase letter, one lowercase letter, one digit, and one special character from (@$!%*?_&)")
            return
        
        # If all validations pass, adds the user to the database
        database.add_teacher(username, fullname, 'Normal Teacher',' ', 0, ' ')
        database.store_password(username, password)

        for x in range(4):
            day = self.days[x] # Iterates the first four days of the week
            for i in range(7): # Iterates through the 7 lessons a day
                database.add_lesson(username, day, i+1, "Empty", "Empty", "None") # Adds default empty entries in the timetable
                self.controller.current_user = username
                self.controller.current_role = 'Normal Teacher' # Sets role to Normal teacher
        for i in range(5): # Iterates similarly for Friday
            database.add_lesson(username, "Friday", i+1, "Empty", "Empty", "None")

        messagebox.showinfo("Registration Successful!", "Contact an SLT member to get your timetable configured.") # Informs the user of successful registration
        self.controller.frames[TeacherScreen].update_welcome_message() # Updates the welcome message with the teacher's name
        self.clear_entries() # Clears the entry fields

    def clear_entries(self):
        """Clear all input entry fields."""
        self.fullname.delete(0, tk.END)
        self.username.delete(0, tk.END)
        self.password.delete(0, tk.END)
        self.repeated_password.delete(0, tk.END)

        # Updates the appropriate screens and raises the correct screen based on role
        self.controller.frames[AccessDatabaseScreen].update_treeview()
        if self.controller.current_role == "SLT":
            self.controller.frames[SLTScreen].timetable.update_timetable()
        elif self.controller.current_role == "Normal Teacher":
            self.controller.frames[TeacherScreen].timetable.update_timetable()
            self.controller.show_frame(TeacherScreen)
        elif self.controller.current_role == None:
            self.controller.show_frame(MainMenu)

    def binder(self, button):
        button.bind("<Enter>", lambda e: self.on_enter(button, "#cacaca"))
        button.bind("<Leave>", lambda e: self.on_leave(button, "SystemButtonFace"))

    def on_enter(self, button, backcolour):
        button.config(background=backcolour)
    
    def on_leave(self, button, backcolour):
        button.config(background=backcolour)

class LoginScreen(tk.Frame):
    """Login Screen for existing users to access their account."""

    def __init__(self, parent, controller):
        """Initializes the LoginScreen class"""
        super().__init__(parent)
        self.controller = controller

        # Create labels and entry fields for user login
        tk.Label(self, text="Username:", font=("Times", 14)).grid(row=2, column=1, padx=160, pady=5, sticky="w")
        self.username = tk.Entry(self, width=50)
        self.username.grid(row=2, column=1, padx=250, pady=30)

        tk.Label(self, text="Password:", font=("Times", 14)).grid(row=3, column=1, padx=160, pady=0, sticky="w")
        self.password = tk.Entry(self, show="*", width=50)
        self.password.grid(row=3, column=1, padx=250, pady=5, sticky="n")

        login = tk.Button(self, text="Login", width=20, height=2, relief="groove", 
                  command=lambda: self.login_user())
        login.grid(row=4, column=1, pady=20)

        cancel = tk.Button(self, text="Cancel", width=20, height=2, relief="groove", 
                  command=lambda: self.clear_entries())
        cancel.grid(row=5, column=1, pady=10)
        
        # Binds hover effects for buttons
        controller.binder(login)
        controller.binder(cancel)

    def login_user(self):
        """Handles login authentication and role-based redirection."""
        username = self.username.get().strip().lower()
        password = self.password.get().strip()

        # Checks if all fields are filled
        if not username or not password:
            messagebox.showerror("Error", "All fields are required!")
            return

        # Validates credentials by checking against the database
        if database.verify_password(username, password) == True:
            role = database.get_role(username)
            self.controller.current_user = username

            if role == "SLT":
                self.controller.frames[SLTScreen].update_welcome_message()
                self.controller.current_role = 'SLT'
                self.controller.frames[SLTScreen].timetable.update_timetable()
                self.controller.show_frame(SLTScreen)
                self.clear_entries()
            else:
                self.controller.frames[TeacherScreen].update_welcome_message()
                self.controller.current_role = 'Normal Teacher'
                self.controller.frames[TeacherScreen].timetable.update_timetable()
                self.controller.show_frame(TeacherScreen)
                self.clear_entries()
        else:
            messagebox.showerror("Error", "Invalid username or password!")

    def clear_entries(self):
        """Clear all entry fields."""
        self.username.delete(0, tk.END)
        self.password.delete(0, tk.END)
        if self.controller.current_role == None:
            self.controller.show_frame(MainMenu)

class Timetable(ttk.Frame):
    """Timetable widget for SLT and Teacher screens."""

    def __init__(self, parent, controller):
        """Initialize the Timetable class"""
        super().__init__(parent)
        self.controller = controller

        # Get todays weekday
        self.weekday = datetime.datetime.today().strftime('%A') # Determines and stores the current day
    
        # Determine number of lessons: Monday-Thursday = 7, Friday = 5,
        self.num_lessons = 5 if self.weekday == "Friday" else 7 # Sets the number of lessons based on the day

        # Creates column headers for the timetable
        if self.weekday == "Friday":
            self.columns = ["Lesson: "] + [f"L{i+1}" for i in range(self.num_lessons)]
        else:
            self.columns = ["Lesson: "] + [f"L{i+1}" for i in range(self.num_lessons)]

        #Binds double click to the timetable
        self.bind("<Double-1>", self.on_double_click)

        style = ttk.Style() # Creates a style variable
        style.theme_use('clam') # Sets the theme of the timetable cells
        style.configure("Treeview", rowheight=40) # Configures row height

        # Creates the treeview widget to display the timetable
        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=3, selectmode="none", style="Treeview")
        
        self.tree.bind('<Button-1>', "break") # Prevents default behaviour when button 1 is clicked
        self.tree.bind("<Double-1>", self.on_double_click) # Binds double-click event
        self.tree.bind("<Motion>", self.on_hover) # Binds the mouse motion event so it runs when it hovers
        self.tree.bind("<Leave>", self.on_leave) # Bind mouse leave event

        self.tree.tag_configure('focus', background='#D3D3D3') # Configures background colour to darken for when a row is hovered over

        # Set headers for the timetable columns
        for col in self.columns:
            self.tree.heading(col, text=col) # Sets column headings
            self.tree.column(col, anchor="center", stretch=True) # Center aligns and stretches columns
            if col == "Lesson: ":
                self.tree.column(col, width=100, anchor="center")
            else:
                self.tree.column(col, width=60, anchor="center")

        # Insert default values into the timetable based on the current weekday
        if self.weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            self.tree.insert("", "end", values=["Subject"] + ["Empty"] * self.num_lessons) # Insert subject row
            self.tree.insert("", "end", values=["Class"] + ["Empty"] * self.num_lessons) # Insert class row
            self.tree.insert("", "end", values=["Substitute"] + ["None"] * self.num_lessons) # Insert substitute row
            self.tree.pack(pady=10, padx=10, fill="x")
        else:
            self.tree.insert("", "end", values=["Subject"] + [" "] * 7)
            self.tree.insert("", "end", values=["Class"] + [" "] * 7)
            self.tree.insert("", "end", values=["Substitute"] + [" "] * 7)
            self.tree.pack(pady=10, padx=10, fill="x")
        
    def update_timetable(self):
        """Update the timetable with the current user's lessons."""
        if self.weekday in ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]:
            
            connection = sqlite3.connect("MyTimetable.db")
            cursor = connection.cursor()

            self.tree.delete(*self.tree.get_children()) # Clear existing timetable entries

            # Query to fetch lessons for the current user based on the weekday
            cursor.execute(f"""SELECT Subject, Class, Substitute
                            FROM {self.weekday}Lessons
                            WHERE Username = ? 
                            ORDER BY Lesson_Number""", (self.controller.current_user,))
            lessons = cursor.fetchall() # Fetches all the lessons

            # Extracts the subjects, classes, and substitutes from the lessons lists
            subjects = [lesson[0] for lesson in lessons] # List of subjects
            classes = [lesson[1] for lesson in lessons] # List of classes
            substitutes = [lesson[2] for lesson in lessons] # List of substitutes

            # Insert the fetched data into the timetable
            self.tree.insert("", "end", values=["Subject"] + subjects)
            self.tree.insert("", "end", values=["Class"] + classes)
            self.tree.insert("", "end", values=["Substitute"] + substitutes)

            self.tree.pack(pady=10, padx=10, fill="x")

            connection.close()

    def on_double_click(self, event):
        """Handles double-click events on the timetable"""
        if self.tree.identify_region(event.x, event.y) == "heading":
            return "break" # Prevents editing if double-clicking on the header

        # Identifies double clicked region
        region_clicked = self.identify(event.x, event.y)

        # Get the item and column at the clicked position
        item = self.tree.identify_row(event.y) # Identify the row clicked
        column = self.tree.identify_column(event.x) # Identify the column clicked

        # Get the value of the item in the column
        value = self.tree.set(item, column)
        rows = self.tree.get_children()

        # Open a popup to enter the new value
        if isinstance(self.master, (AddTeacherScreen, EditDatabaseScreen, AdminEditDatabase)):
            if value in ("Subject","Class","Substitute"):
                return "break" # Prevents editing the header column
            elif item == rows[0]:
                new_value = simpledialog.askstring("Edit Contents", f"Enter new subject name:") # Prompt for new subject
                try:
                    new_value = new_value.strip()
                except:
                    pass

                if new_value is not None:
                    self.tree.set(item, column, new_value)

            elif item == rows[1]:
                new_value = simpledialog.askstring("Edit Contents", f"Enter new class location:") # Prompt for new class
                try:
                    new_value = new_value.strip()
                except:
                    pass

                if new_value is not None:
                    self.tree.set(item, column, new_value)

            elif item == rows[2]:
                new_value = simpledialog.askstring("Edit Contents", f"Enter new substitute, leave empty if none:") # Prompt for new substituting teacher
                try:
                    new_value = new_value.strip()
                except:
                    pass

                if new_value is not None:
                    self.tree.set(item, column, new_value)

    def on_hover(self, event):
        """Highlight the cell that the mouse is over."""
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)

        try:
            value = self.tree.set(item, column)
        except:
            return "break"

        if self.tree.identify_region(event.x, event.y) == "heading":
            return "break" # Prevents action if hovering over the header
        
        if item:
            for i in self.tree.get_children():
                self.tree.item(i, tags=()) # Clears tags for all items
            self.tree.item(item, tags=('focus')) # Highlight the current item
    
    def on_leave(self, event):
        """Reset the highlight when the mouse leaves the timetable"""
        for i in self.tree.get_children():
            self.tree.item(i, tags=()) # Clears tags for all the items

    def Create_Empty_Timetable(self):
        """Create an empty timetable for Monday to Thursday."""
        self.tree.delete(*self.tree.get_children()) # Clears existing timetable entries
        self.columns = ["Lesson: "] + [f"L{i+1}" for i in range(7)] # Define columns for the timetable
        self.tree["columns"] = self.columns

        # Set headers for the timetable columns
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", stretch=True)
            if col == "Lesson: ":
                self.tree.column(col, width=100, anchor="center")
            else:
                self.tree.column(col, width=60, anchor="center")

        # Inserts default empty values into the timetable
        self.tree.insert("", "end", values=["Subject"] + ["Empty"] * 7)
        self.tree.insert("", "end", values=["Class"] + ["Empty"] * 7)
        self.tree.insert("", "end", values=["Substitute"] + ["None"] * 7)

    def Create_Friday_Timetable(self):
        """Create a Friday timetable."""
        self.tree.delete(*self.tree.get_children())
        self.columns = ["Lesson: "] + [f"L{i+1}" for i in range(5)]
        self.tree["columns"] = self.columns

        # Set headers
        for col in self.columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", stretch=True)
            if col == "Lesson: ":
                self.tree.column(col, width=100, anchor="center")
            else:
                self.tree.column(col, width=60, anchor="center")

        self.tree.insert("", "end", values=["Subject"] + ["Empty"] * 5)
        self.tree.insert("", "end", values=["Class"] + ["Empty"] * 5)
        self.tree.insert("", "end", values=["Substitute"] + ["None"] * 5)

class SLTScreen(tk.Frame):
    """Senior Leader Teacher Screen."""

    def __init__(self, parent, controller):
        """Initializes the SLTScreen class"""
        super().__init__(parent)
        self.controller = controller

        self.welcome_label = tk.Label(self, text=("   Welcome, Admin   "), borderwidth=2, relief="solid", font=("Times", 16), height=2)
        self.welcome_label.place(x=0, y=0)

        # Creates buttons for various SLT tasks
        tk.LabelFrame(self, width=200, height=400, relief="solid").grid(row=1, column=0, sticky="w")

        add = tk.Button(self, text="Add Teacher Data", width=26, height=7, relief="groove", 
                  command=lambda: controller.show_frame(AddTeacherScreen))
        add.grid(row=1, column=0, sticky="n", pady=55)

        sltabsent = tk.Button(self, text="Mark a Teacher Absent", width=26, height=3, relief="groove", 
                  command=lambda: controller.show_frame(SLTAbsenceScreen))
        sltabsent.grid(row=1, column=0, pady=65)

        view = tk.Button(self, text="View Teacher Database", width=26, height=7, relief="groove", 
                  command=lambda: controller.show_frame(AccessDatabaseScreen))
        view.grid(row=1, column=0, sticky="s", pady=55)

        absent = tk.Button(self, text="Inform My Absence", width=20, height=3, relief="groove",
                  command=lambda: controller.show_frame(AbsenceScreen))
        absent.place(x=650, y=0)

        signout = tk.Button(self, text="Sign Out", width=15, height=2, relief="groove", 
                  command=lambda: self.sign_out())
        signout.place(x=685, y=55)

        # Binds all the buttons with hover functionality
        controller.binder(add)
        controller.binder(sltabsent)
        controller.binder(view)
        controller.binder(absent)
        controller.binder(signout)

        #to instantly run the algorithm for testing purposes
        tk.Button(self, text="Run Cover Allocation Test", width=20, height=2, relief="groove",
                  command=lambda: MainAlgorithm(self.controller).cover_allocation()).place(x=685, y=110)

        weekday = datetime.datetime.today().strftime('%A')

        # Label displaying today's date
        self.day_label = tk.Label(self, text=f"Today is {weekday}", font=("Arial", 16, "bold"))
        self.day_label.place(x=415, y=120)
        
        # Add timetable inside SLTScreen
        self.timetable = Timetable(self, controller)
        if weekday == "Friday":
            self.timetable.place(x=285, y=150)
        else:
            self.timetable.place(x=230, y=150)  # Adjust position as needed

        # Adds a clock on the screen
        self.clock = tk.Label(self, text = "", font=('Times', 40, 'bold'))
        self.clock.place(x=350, y=0)
        self.time()

        self.welcome_label.lift()

    def update_welcome_message(self):
        """Update the welcome message with the logged-in username."""
        fullname = database.get_fullname(self.controller.current_user)
        self.welcome_label.config(text=f"   Welcome, {fullname}   ")
    
    def sign_out(self):
        # Forgets the user's username and role to reset permissions
        self.controller.current_user = None
        self.controller.current_role = None
        
        self.controller.show_frame(MainMenu)

    def time(self):
        string = strftime('%H:%M %p')
        self.clock.config(text=string)
        self.clock.after(10000, self.time) #Attempts to update the clock every 10 seconds

class TeacherScreen(tk.Frame):
    """Normal Teacher Screen."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        self.welcome_label = tk.Label(self, text=("   Welcome, Admin   "), borderwidth=2, relief="solid", font=("Times", 16), height=2)
        self.welcome_label.grid(row=0, column=0, sticky="w")

        absent = tk.Button(self, text="Inform My Absence", width=20, height=3, relief="groove",
                  command=lambda: controller.show_frame(AbsenceScreen))
        absent.place(x=650, y=0)

        signout = tk.Button(self, text="Sign Out", width=15, height=2, relief="groove", 
                  command=lambda: self.sign_out())
        signout.place(x=685, y=55)

        # Binds hover effect to buttons
        controller.binder(absent)
        controller.binder(signout)
        
        # Gets today's weekday
        weekday = datetime.datetime.today().strftime('%A')

        # Label displaying today's date
        self.day_label = tk.Label(self, text=f"Today is {weekday}", font=("Arial", 16, "bold"))
        self.day_label.place(x=315, y=78)
        
        # Add timetable inside SLTScreen
        self.timetable = Timetable(self, controller)

        # Determines position based on whether its on friday or the other days of the week
        if weekday == "Friday":
            self.timetable.place(x=185, y=150)
        else:
            self.timetable.place(x=130, y=110) # Adjust position as needed

        # Creates a clock on the screen
        self.clock = tk.Label(self, text = "", font=('Times', 40, 'bold'))
        self.clock.place(x=350, y=0)
        self.time() # Starts the clock

    def update_welcome_message(self):
        """Update the welcome message with the logged-in username."""
        fullname = database.get_fullname(self.controller.current_user)
        self.welcome_label.config(text=f"   Welcome, {fullname}   ")

    def sign_out(self):
        # Resets the current user and role to none to strip permissions
        self.controller.current_user = None
        self.controller.current_role = None
        self.controller.show_frame(MainMenu) # Raises the MainMenu screen

    def time(self):
        string = strftime('%H:%M %p')
        self.clock.config(text=string) # Updates the clock label with the new time
        self.clock.after(10000, self.time) # Checks the time every 10 seconds and attempts to update it

class AbsenceScreen(tk.Frame):
    """Absence Screen."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Creates buttons for navigation of absent options based on user need
        today = tk.Button(self, text="Only Absent Today", width=30, height=5, relief="groove",
                  command=lambda: self.only_absent_today())
        today.grid(row=0, column=0, padx=110, pady=110)

        multiple = tk.Button(self, text="Mark Multiple Days Absent", width=30, height=5, relief="groove",
                  command=lambda: controller.show_frame(MarkDaysAbsent))
        multiple.grid(row=0, column=1, padx=30, pady=110)

        cancel = tk.Button(self, text="Cancel", width=15, height=2, relief="groove",
                  command=lambda: controller.go_back())
        cancel.place(x=342, y=210)

        # Binds the buttons for hover effect
        controller.binder(today)
        controller.binder(multiple)
        controller.binder(cancel)
        
    def only_absent_today(self):
        now = datetime.datetime.now() # Gets the current time
        cutoff_time = datetime.time(6, 30) # Sets the latest time for Non-SLT members to mark absence today

        # Avoids a teacher getting marked absent twice for the same day
        if database.is_absent(self.controller.current_user, datetime.datetime.today().date()):
            messagebox.showerror("Error", "You are already marked as absent today!")
            return

        elif self.controller.current_role != "SLT":
            if now.time() <= cutoff_time: # Checks that the current time is before the cutoff time
                dates = AbsenceDates()
                dates.sorted_dates = [datetime.datetime.today().date()]
                self.controller.show_frame(AbsenceConfirmation)
            else:
                messagebox.showerror("Error", "Cannot select today as it is past 6:30 AM!\nContact an SLT member for support")
                return
        
        else:
            dates = AbsenceDates()
            dates.sorted_dates = [datetime.datetime.today().date()] # Sorts the dates
            self.controller.show_frame(AbsenceConfirmation) # Raises the Absence confirmation screen

class SLTAbsenceScreen(tk.Frame):
    """SLT Absence Screen."""
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        today = tk.Button(self, text="Only Absent Today", width=30, height=5, relief="groove",
                  command=lambda: self.only_absent_today())
        today.grid(row=0, column=0, padx=110, pady=110)

        multiple = tk.Button(self, text="Mark Multiple Days Absent", width=30, height=5, relief="groove",
                  command=lambda: controller.show_frame(SLTMarkDaysAbsent))
        multiple.grid(row=0, column=1, padx=30, pady=110)
        
        cancel = tk.Button(self, text="Cancel", width=15, height=2, relief="groove",
                  command=lambda: controller.go_back())
        cancel.place(x=342, y=210)

        controller.binder(today)
        controller.binder(multiple)
        controller.binder(cancel)
        
    def only_absent_today(self):
        dates = AbsenceDates()
        dates.sorted_dates = [datetime.datetime.today().date()]
        self.controller.show_frame(SLTAbsenceConfirmation)
        
class MyCalendar(tkc.Calendar):
    """Custom Calender class to restrict selection to specific weekdays"""

    def __init__(self, master=None, allowed_weekdays=(calendar.MONDAY,), **kw):
        """Initializes the Calendar class with the first allowed weekday being Monday"""
        self._select_only = allowed_weekdays # Stores the allowed weekdays
        tkc.Calendar.__init__(self, master, **kw)

        # Ensures the selected date is within the allowed weekdays
        if self._sel_date and not (self._sel_date.isoweekday() - 1) in allowed_weekdays:
            year, week, wday = self._sel_date.isocalendar() # Gets the year, week, and weekday of the selected date

            # Finds the next allowed weekday
            next_wday = max(allowed_weekdays, key=lambda d: (d - wday + 1) > 0) + 1
            sel_date = self.date.fromisocalendar(year, week + int(next_wday < wday), next_wday) # Calculates the next selectable date
            self.selection_set(sel_date)

    def _display_calendar(self):
        """Displays the calendar and disables selection for non allowed weekday"""
        tkc.Calendar._display_calendar(self)

        for i in range(6): # Iterates through the rows of the calendar
            for j in range(7): # Iterates through the columns / days of the week
                if j in self._select_only: # Check if the current day of the week is a allowed weekday
                    continue # Skips allowed weekdays
                self._calendar[i][j].state(['disabled']) # Disables the button for non allowed weekdays

class MarkDaysAbsent(tk.Frame):
    """Screen for marking multiple days absent"""

    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller
        self.sorted_dates = set() # Set to store selected absence dates

        # Get current date and time
        now = datetime.datetime.now()
        current_date = now.date()
        cutoff_time = datetime.time(6, 30) # Sets the latest time for marking absence to 6:30

        # If time is past 6:30 AM, today cannot be selected
        self.min_selectable_date = current_date if now.time() <= cutoff_time else current_date + datetime.timedelta(days=1)

        # Title Label
        tk.Label(self, text="Select Multiple Days of Absence", font=("Times", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))

        # Calendar Widget
        self.cal = MyCalendar(self, allowed_weekdays=(calendar.MONDAY, calendar.TUESDAY, calendar.WEDNESDAY, calendar.THURSDAY, calendar.FRIDAY),
                               selectmode="day", mindate=self.min_selectable_date, width=400, height=300)
        self.cal.grid(row=1, column=0, columnspan=2, padx=276, pady=(5, 10))

        # Selected Dates Listbox
        tk.Label(self, text="Selected Dates:", font=("Times", 12)).grid(row=2, column=0, columnspan=2, pady=(5, 0))
        self.selected_dates_listbox = tk.Listbox(self, height=5, width=30) # Displats selected dates
        self.selected_dates_listbox.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 5))

        # Instructions to aid users improving user friendliness
        tk.Label(self, text="Select date from the calender \nand click 'Add Date'\n to add it to the list.", font=("Times", 8)).place(x=155, y=300, anchor="w")
        tk.Label(self, text="Select date from the list \nand click 'Remove Date'\n to remove a date from the list.", font=("Times", 8)).place(x=500, y=300, anchor="w")

        # Add & Remove Buttons
        self.add_date_btn = tk.Button(self, text="Add Date", width=12, relief="groove", 
                                      command=lambda: self.add_date())
        
        self.add_date_btn.grid(row=4, column=0, padx=5, pady=1, sticky="e")

        self.remove_date_btn = tk.Button(self, text="Remove Date", width=12, relief="groove", 
                                         command=lambda: self.remove_selected_date())
        
        self.remove_date_btn.grid(row=4, column=1, padx=5, pady=1, sticky="w")

        # Cancel & Confirm Buttons
        self.cancel_btn = tk.Button(self, text="Cancel", width=20, height=3, relief="groove", 
                                    command=lambda: self.clear_entries())
        
        self.cancel_btn.place(x=0, y=345)
        
        self.confirm_btn = tk.Button(self, text="Confirm", width=20, height=3, relief="groove", 
                                     command=lambda: self.confirm_absences())
        self.confirm_btn.place(x=651, y=345)

        # Bind hover effects for buttons
        controller.binder(self.add_date_btn)
        controller.binder(self.remove_date_btn)
        controller.binder(self.cancel_btn)
        controller.binder(self.confirm_btn)

        # Store selected dates
        self.selected_dates = set()

    def add_date(self):
        """Adds the selected date from the calendar to the listbox."""
        selected_date = self.cal.get_date() # Get the selected date from the calendar
        formatted_date = datetime.datetime.strptime(selected_date, "%m/%d/%y").date() # Format the date

        # Prevent selecting past dates
        if formatted_date < self.min_selectable_date:
            messagebox.showerror("Error", "Cannot select past dates!")
            return # Exit the method if validation fails

        # Add to set (avoid duplicates)
        self.selected_dates.add(formatted_date)

        # Updates Listbox
        self.selected_dates_listbox.delete(0, tk.END) # Clears the listbox
        for date in sorted(self.selected_dates): # Sorts and displays selected dates
            self.selected_dates_listbox.insert(tk.END, date) # Inserts each date into the listbox

    def remove_selected_date(self):
        """Removes a selected date from the listbox."""
        try:
            selected_index = self.selected_dates_listbox.curselection()[0]  # Get selected item index
            selected_date = self.selected_dates_listbox.get(selected_index)  # Get date string
            self.selected_dates.remove(datetime.datetime.strptime(selected_date, "%Y-%m-%d").date())  # Convert back to date
            self.selected_dates_listbox.delete(selected_index)  # Remove from listbox
        except IndexError:
            messagebox.showerror("Error", "No date selected!") # Use of exception handling

    def confirm_absences(self):
        """Processes selected absence dates."""
        if not self.selected_dates:
            messagebox.showerror("Error", "Please select at least one date!")
            return # Exit if no dates are selected

        # Convert to sorted list
        sorted_dates = self.merge_sort(self.selected_dates) # Sorts the selected dates

        dates = AbsenceDates() # Creates an instance of AbsenceeDtaes
        dates.sorted_dates = sorted_dates # Assigns the sorted dates to the instance

        for x in range(len(sorted_dates)):
            if database.is_absent(self.controller.current_user, sorted_dates[x]):
                messagebox.showerror("Error", f"You are already marked as absent on {sorted_dates[x]}!")
                return # Exits if the user is already marked absent

        self.clear_entries() # Clears the entries after confirmation

        # Navigate to the next screen
        self.controller.show_frame(AbsenceConfirmation) # Raises the AbsenceConfirmation screen

    def merge_sort(self, dates): # Use of Efficient sorting algorithm
        """Performs merge sort on the list of dates"""

        dates = list(dates) # Converts the set to a list

        if len(dates) <= 1:
            return dates # Returns if the list consists of only 1 item or is empty since its already sorted
        
        mid = len(dates) // 2 # Finds the midpoint
        # Use of recursive algorithms
        left_half = self.merge_sort(dates[:mid]) # Recursively sorts the left half
        right_half = self.merge_sort(dates[mid:]) # Recursively sorts the right half

        return self.merge(left_half, right_half)
    
    def merge(self, left, right):
        """Merges two sorted lists"""
        sorted_list = [] # List to hold the merged result
        while left and right: # Checks that neither of the lists are empty
            if left[0] < right[0]: # Compares the first date of each half
                sorted_list.append(left.pop(0)) # Appends the left date if its smaller and pops it from the left side
            else:
                sorted_list.append(right.pop(0)) # Appends the right daye if its smaller and pops it from the right side
        sorted_list.extend(left or right) # Adds the remaining elements of the none empty half
        return sorted_list # Returns the merged sorted list

    def clear_entries(self):
        """Clear all selected dates and resets the calendar"""
        self.selected_dates.clear()
        self.selected_dates_listbox.delete(0, tk.END)
        
        self.cal.selection_set(datetime.datetime.now().date())

        self.controller.show_frame(AbsenceScreen) # Raises the Absence screen
        
class SLTMarkDaysAbsent(tk.Frame):
    """Screen for SLT members to mark teachers multiple days absent"""

    def __init__(self, parent, controller):
        super().__init__(parent)

        self.controller = controller

        # Get current date and time
        now = datetime.datetime.now()
        current_date = now.date()

        self.min_selectable_date = current_date

        # Title Label
        tk.Label(self, text="Select Multiple Days of Absence", font=("Times", 14, "bold")).grid(row=0, column=0, columnspan=2, pady=(10, 5))

        # Calendar Widget
        self.cal = MyCalendar(self, allowed_weekdays=(calendar.MONDAY, calendar.TUESDAY, calendar.WEDNESDAY, calendar.THURSDAY, calendar.FRIDAY),
                               selectmode="day", mindate=self.min_selectable_date, width=400, height=300)
        self.cal.grid(row=1, column=0, columnspan=2, padx=276, pady=(5, 10))

        # Selected Dates Listbox
        tk.Label(self, text="Selected Dates:", font=("Times", 12)).grid(row=2, column=0, columnspan=2, pady=(5, 0))
        self.selected_dates_listbox = tk.Listbox(self, height=5, width=30)
        self.selected_dates_listbox.grid(row=3, column=0, columnspan=2, padx=10, pady=(0, 5))

        tk.Label(self, text="Select date from the calender \nand click 'Add Date'\n to add it to the list.", font=("Times", 8)).place(x=155, y=300, anchor="w")
        tk.Label(self, text="Select date from the list \nand click 'Remove Date'\n to remove a date from the list.", font=("Times", 8)).place(x=500, y=300, anchor="w")

        # Add & Remove Buttons
        self.add_date_btn = tk.Button(self, text="Add Date", width=12, relief="groove", 
                                      command=lambda: self.add_date())
        
        self.add_date_btn.grid(row=4, column=0, padx=5, pady=1, sticky="e")

        self.remove_date_btn = tk.Button(self, text="Remove Date", width=12, relief="groove", 
                                         command=lambda: self.remove_selected_date())
        
        self.remove_date_btn.grid(row=4, column=1, padx=5, pady=1, sticky="w")

        # Cancel & Confirm Buttons
        self.cancel_btn = tk.Button(self, text="Cancel", width=20, height=3, relief="groove", 
                                    command=lambda: self.clear_entries())
        self.cancel_btn.place(x=0, y=345)
        
        self.confirm_btn = tk.Button(self, text="Confirm", width=20, height=3, relief="groove", 
                                     command=lambda: self.confirm_absences())
        self.confirm_btn.place(x=651, y=345)

        controller.binder(self.add_date_btn)
        controller.binder(self.remove_date_btn)
        controller.binder(self.cancel_btn)
        controller.binder(self.confirm_btn)

        # Store selected dates
        self.selected_dates = set()

    def add_date(self):
        """Adds the selected date from the calendar to the listbox."""
        selected_date = self.cal.get_date()
        formatted_date = datetime.datetime.strptime(selected_date, "%m/%d/%y").date()

        # Prevent selecting past dates
        if formatted_date < self.min_selectable_date:
            messagebox.showerror("Error", "Cannot select past dates!")
            return

        # Add to set (avoid duplicates)
        self.selected_dates.add(formatted_date)

        # Update Listbox
        self.selected_dates_listbox.delete(0, tk.END)
        for date in sorted(self.selected_dates):
            self.selected_dates_listbox.insert(tk.END, date)

    def remove_selected_date(self):
        """Removes a selected date from the listbox."""
        try:
            selected_index = self.selected_dates_listbox.curselection()[0]  # Get selected item index
            selected_date = self.selected_dates_listbox.get(selected_index)  # Get date string
            self.selected_dates.remove(datetime.datetime.strptime(selected_date, "%Y-%m-%d").date())  # Convert back to date
            self.selected_dates_listbox.delete(selected_index)  # Remove from listbox
        except IndexError:
            messagebox.showerror("Error", "No date selected!")

    def confirm_absences(self):
        """Processes selected absence dates."""
        if not self.selected_dates:
            messagebox.showerror("Error", "Please select at least one date!")
            return # Exit if no dates are selected

        # Convert to sorted list
        sorted_dates = self.merge_sort(self.selected_dates)
        
        dates = AbsenceDates()
        dates.sorted_dates = sorted_dates

        self.clear_entries()

        # Navigate to the next screen
        self.controller.show_frame(SLTAbsenceConfirmation)

    def merge_sort(self, dates):
        """Performs merge sort on the list of dates"""

        dates = list(dates)

        if len(dates) <= 1:
            return dates
        
        mid = len(dates) // 2
        left_half = self.merge_sort(dates[:mid])
        right_half = self.merge_sort(dates[mid:])

        return self.merge(left_half, right_half)
    
    def merge(self, left, right):
        """Merges two sorted lists"""
        sorted_list = []
        while left and right:
            if left[0] < right[0]:
                sorted_list.append(left.pop(0))
            else:
                sorted_list.append(right.pop(0))
        sorted_list.extend(left or right)
        return sorted_list

    def clear_entries(self):
        self.selected_dates.clear()
        self.selected_dates_listbox.delete(0, tk.END)

        self.cal.selection_set(datetime.datetime.now().date())

        self.controller.show_frame(SLTAbsenceScreen)

class AbsenceDates:
    """Class to manage temporary saving and moving of absence dates"""

    sorted_dates = [] # Class variable to hold the sorted absence dates
    _instance = None

    def __new__(cls):
        """Creates a new instance of AbsenceDates or returns the existing instance"""
        if cls._instance is None: # Checks if an instance already exists
            cls._instance = super(AbsenceDates, cls).__new__(cls) # Creates a new instance
            cls._instance.sorted_dates = [] # Initializes the sorted_dates list
        return cls._instance # Returns the instance
    
class AbsenceConfirmation(tk.Frame):
    """Screen to confirm the absence dates selected"""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text="Reason:", font=("Times", 18)).pack(padx=103.5, pady=40)
        self.reason = tk.Entry(self, width=50)
        self.reason.pack(padx=250, pady=0, side="top")

        cancel = tk.Button(self, text="Cancel", width=10, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        cancel.place(x=80, y=225)
        
        tk.Label(self, text="Are you sure?", font=("Times", 14)).pack(padx=103.5, pady=10)
        tk.Label(self, text="(You will be considered absent!)", font=("Times", 14)).pack(padx=103.5, pady=0)
                
        confirm = tk.Button(self, text="Confirm", width=10, height=2, relief="groove",
                  command=lambda: self.save_absence())
        confirm.place(x=360, y=225)

        controller.binder(cancel)
        controller.binder(confirm)

    def save_absence(self):
        absences = AbsenceDates() # Extracts the dates from the AbsenceDates instance
        username = self.controller.current_user # Gets current username
        fullname = database.get_fullname(username)
        dates = absences.sorted_dates
        reason = self.reason.get()
        numofdates = len(dates)

        if reason == "" or not re.match(r"^[A-Za-z\s]+$", reason):  # Allow letters and spaces
            messagebox.showerror("Error", "Please enter a valid reason for the absence!")
            return
        
        # Open the absence log file to append absence records
        f = open("AbsenceLog.txt", "a") # Open file in append mode

        for x in range(numofdates): # Iterates through the absence dates
            date = dates[x] # Get each date
            line = f"{fullname} is absent on the {date}. Reason = {reason}\n" # Formats the log entry
            f.write(line) # Writes the entry to the file
            database.add_absence(username, date, reason) # Saves absence details to the database
        f.close() # Close the file

        # Reopen the absence log file to sort entries
        f = open("AbsenceLog.txt", "r") # Open file in read mode
        content = f.readlines() # Read all the lines
        content.sort(key=lambda x: datetime.datetime.strptime(x.split("is absent on the ")[1].split(". Reason =")[0], "%Y-%m-%d")) # Sort entries by date
        f.close() # Close the file

        # Write the sorted content back to the file
        f = open("AbsenceLog.txt", "w") # Open file in write mode
        f.writelines(content) # Write sorted entries back to the file
        f.close() # Close the file

        # Show success message
        messagebox.showinfo("Success", f"You are marked Absent for: {', '.join(map(str, dates))}")
        
        self.clear_entries()
        self.controller.go_back() # Navigate back to the approporiate previous screen
    
    def clear_entries(self):
        self.reason.delete(0, tk.END) # Resets reason entry box to empty

        self.controller.show_frame(AbsenceScreen) # Raises the absence screen
        
class SLTAbsenceConfirmation(tk.Frame):
    """Screen for SLT members to confirm absences"""

    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Label for selecting the teacher's username
        tk.Label(self, text="Teacher Username:", font=("Times", 16)).pack(padx=103.5, pady=(10,0))

        # Combobox for selecting absent teacher's username
        self.absent_teacher = ttk.Combobox(self, values=database.get_all_usernames(), width=50, state="normal") # Dropdown for usernames
        self.absent_teacher.pack(padx=250, pady=(0, 15), side="top")

        self.absent_teacher.bind("<KeyRelease>", self.checkkey) # Binds key release for filtering usernames

        tk.Label(self, text="Reason:", font=("Times", 16)).pack(padx=103.5, pady=(0,0))
        self.reason = tk.Entry(self, width=50)
        self.reason.pack(padx=250, pady=(0, 15), side="top")

        cancel = tk.Button(self, text="Cancel", width=10, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        cancel.place(x=80, y=235)
        
        # Confirmation prompt
        tk.Label(self, text="Are you sure?", font=("Times", 14)).pack(padx=103.5, pady=10)
        tk.Label(self, text="(This teacher will be considered absent!)", font=("Times", 14)).pack(padx=103.5, pady=0)
                
        confirm = tk.Button(self, text="Confirm", width=10, height=2, relief="groove",
                  command=lambda: self.save_absence())
        confirm.place(x=360, y=235)

        controller.binder(cancel)
        controller.binder(confirm)
        
    def save_absence(self):
        """Save the absence details to the database and log file."""
        absences = AbsenceDates()  # Create an instance of AbsenceDates to get selected dates
        username = self.absent_teacher.get()  # Get the selected username from the combobox
        fullname = database.get_fullname(username)  # Fetch the full name from the database
        dates = absences.sorted_dates  # Get the sorted absence dates
        reason = self.reason.get()  # Get the reason for absence
        numofdates = len(dates)  # Count the number of absence dates
        now = datetime.datetime.now().time()  # Get the current date and time
        first_time = datetime.time(6, 30)  # Define the cutoff time for marking absence
        last_time = datetime.time(15, 0)  # Define the latest time for marking absence

        # Validate the selected username
        if username not in [item[0] for item in database.get_all_usernames()]:
            messagebox.showerror("Error", "Selected username does not exist!\nPlease select a valid username from the dropdown list.")
            return
        
        # Validate the reason input
        if reason == "" or not re.match(r"^[A-Za-z\s]+$", reason): # Check that the reason isn't empty and consists of alphabetic characters and spaces  
            messagebox.showerror("Error", "Please enter a valid reason for the absence!")
            return
        
        # Checks if the teacher is already marked absent on the selected dates
        for x in range(numofdates):
            if database.is_absent(username, dates[x]):
                messagebox.showerror("Error", f"This teacher is already marked as absent on {dates[x]}!")
                self.clear_entries() # Clears entries if the teacher is already marked absent
                return
        
        f = open("AbsenceLog.txt", "a")

        for x in range(numofdates):
            date = dates[x]
            line = f"{fullname} is absent on the {date}. Reason = {reason}\n"
            f.write(line)
            database.add_absence(username, date, reason)
        f.close()

        f = open("AbsenceLog.txt", "r")
        content = f.readlines()
        content.sort(key=lambda x: datetime.datetime.strptime(x.split("is absent on the ")[1].split(". Reason =")[0], "%Y-%m-%d"))
        f.close()

        f = open("AbsenceLog.txt", "w")
        f.writelines(content)
        f.close()

        #Displays absence success message
        messagebox.showinfo("Success", f"{fullname} is marked Absent for: {', '.join(map(str, dates))}")

        # Checks if the current time is within the allowed range for cover allocation
        if now >= first_time and now <= last_time:
            M = MainAlgorithm(self.controller) # Creates an instance of MainAlgorithm
            M.cover_allocation() # Calls the cover allocation algorithm

        self.clear_entries()
        self.controller.go_back()

    def update_absent_teachers(self):
        """Updates the absent teachers in the combobox"""
        self.absent_teacher.config(values=database.get_all_usernames())

    def clear_entries(self):
        """Clears all the entry fields"""
        self.absent_teacher.delete(0, tk.END)
        self.reason.delete(0, tk.END)

        self.controller.show_frame(SLTAbsenceScreen)

    def checkkey(self, event): 
        """Filers the usernames in the combobox based on user input"""      
        value = self.absent_teacher.get() # Gets the current input

        if value == '':
            data = database.get_all_usernames() # Gets all the username if input is empty
        else:
            #Filers the usernames based on the input value
            data = [item[0] for item in database.get_all_usernames() if value.lower() in item[0].lower()]
            
        self.absent_teacher.config(values=data) # Updates the combobox with filtered username

class AddTeacherScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.counter = 0 # Counter to track the current day of the week
        self.password = None # Placeholder for the generated password

        # Labels and entries for teacher data
        tk.Label(self, text="Teacher Fullname: ", font=("Times", 14)).grid(row=0, column=0, padx=(130, 0), sticky="e")
        self.fullname = tk.Entry(self, width=50)
        self.fullname.grid(row=0, column=1, sticky="w")

        tk.Label(self, text="Teacher Username: ", font=("Times", 14)).grid(row=1, column=0, padx=(130, 0), sticky="e")    
        self.username = tk.Entry(self, width=50)
        self.username.grid(row=1, column=1, sticky="w")

        tk.Label(self, text="Teacher Password: ", font=("Times", 14)).grid(row=2, column=0, padx=(130, 0), sticky="e")

        # Label and button for generating a new password
        create = tk.Button(self, text="Create New Password", width=42, height=1, relief="groove",
                  command=lambda: self.randomize_password())
        create.grid(row=2, column=1, sticky="w")

        # Label and combobox for Teacher Department
        tk.Label(self, text="Teacher Department: ", font=("Times", 14)).grid(row=3, column=0, padx=(130, 0), sticky="e")  

        department_list = ["Mathematics", "English", "Science", "History", "Geography", "MFL", "Art", "Music", "PE", "CS"]
        self.department = ttk.Combobox(self, values=department_list, width=50, state="readonly")
        self.department.grid(row=3, column=1, sticky="w")

        tk.Label(self, text="Cover Limit: ", font=("Times", 14)).grid(row=4, column=0, padx=(130, 0), sticky="e")   
        self.cover_limit = tk.Entry(self, width=50)
        self.cover_limit.grid(row=4, column=1, sticky="w")

        # Instructions for editingg cells to aid user friendliness
        tk.Label(self, text="*Double click a cell to edit", font=("Times", 10, "bold")).grid(row=5, column=0, padx=(130, 0),pady=(15,4), sticky="sw")
        tk.Label(self, text="*Only edit cells with lessons\nLessons left as empty will be considered free", font=("Times", 8, "bold")).place(x=500, y=140)

        # Navigation buttons for changing days
        left = tk.Button(self, text="<--", width=10, height=4, relief="groove",
                  command=lambda: self.decrease_counter())
        left.place(x=54, y=230)
        
        right = tk.Button(self, text="-->", width=10, height=4, relief="groove",
                  command=lambda: self.increase_counter())
        right.place(x=670, y=230)

        # Confirmation and cancel buttons
        cancel = tk.Button(self, text="Cancel", width=20, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        cancel.place(x=0, y=359)

        confirm = tk.Button(self, text="Confirm Data", width=20, height=2, relief="groove",
                  command=lambda: self.confirm_teacher_data())
        confirm.place(x=650, y=359)

        # Binds buttons for hover effects
        controller.binder(create)
        controller.binder(left)
        controller.binder(right)
        controller.binder(cancel)
        controller.binder(confirm)

        # Initializes timetable for each day of the week
        self.timetables = {}
        for i in range(4):
            self.timetables[i] = Timetable(self, controller)
            self.timetables[i].Create_Empty_Timetable() # Creates empty timetable for monday to thursday
        self.timetables[4] = Timetable(self, controller)
        self.timetables[4].Create_Friday_Timetable() # Creates an empty timetable for fridaty

        self.current_timetable = self.timetables[0] # Starts with monday's timetable
        self.current_timetable.place(x=130, y=175)

        # Label to display the current day
        self.day_label = tk.Label(self, text="Monday", font=("Arial", 16, "bold"))
        self.day_label.place(x=350, y=145)

    def increase_counter(self):
        """Increases the day counter to show the next day's timetable"""
        if self.counter < 4:
            self.counter += 1
            self.update_day() # Updates the display to show the next day

    def decrease_counter(self):
        """Decreases the day counter to show the previous day's timetable"""
        if self.counter > 0:
            self.counter -= 1
            self.update_day() # Updates the display to show the previous day

    def update_display(self):
        """Updates the display to show the correct day timetable"""
        self.current_timetable.place_forget() # Hides the current timetable
        self.current_timetable = self.timetables[self.counter] # Get the timetable for the current day
        if self.counter == 4:  # If it's Friday
            self.current_timetable.place(x=190, y=175)
        else:
            self.current_timetable.place(x=130, y=175)

    def update_day(self):
        """Updates the day label and display based on the current counter"""
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.update_daylabel(self.days[self.counter]) # Updates the day label
        self.update_display() # Updates the timetable display

    def update_daylabel(self, day):
        """Updates the day label with the correct day"""
        self.day_label.config(text=f"{day}")
    
    def get_lesson(self, column):
        """Retrieves lesson details from the current timetable for a specific column"""
        values = []
        for item in self.current_timetable.tree.get_children():
            value = self.current_timetable.tree.item(item)['values'][column]
            values.append(value)
        return values

    def get_friday_lesson(self, column):
        """Retrieves lesson details for Friday from the current timetable for a specific column"""
        # Get all three rows directly
        rows = self.current_timetable.tree.get_children()
        
        # Get values from specific column for each row
        subject = self.current_timetable.tree.item(rows[0])['values'][column]
        class_name = self.current_timetable.tree.item(rows[1])['values'][column]
        substitute = self.current_timetable.tree.item(rows[2])['values'][column]
        values = [subject, class_name, substitute] # Returns values as a list
        
        return values
    
    def randomize_password(self):
        """Generates a random password for the teacher"""
        s1 = list(string.ascii_lowercase)
        s2 = list(string.ascii_uppercase)
        s3 = list("@$!%*?_&")
        s4 = list(string.digits)

        random.shuffle(s1)  # Shuffles lowercase letters
        random.shuffle(s2)  # Shuffles uppercase letters
        random.shuffle(s3)  # Shuffles special characters
        random.shuffle(s4)  # Shuffles digits

        result = []

        for x in range(3):
            result.append(s1[x]) # Adds 3 random lowercase letters
            result.append(s2[x]) # Adds 3 random uppercase letters
        
        for x in range(2):
            result.append(s3[x]) # Adds 2 random special characters
            result.append(s4[x]) # Adds 2 random digits
        
        random.shuffle(result) # Shuffles the final password characters

        password = "".join(result) # Sets the password to the shuffled result
        self.password = password # Stores the generated password
        
        messagebox.showinfo("Password Reset", f"The new password is {password}") # Shows the new password in a message box

    def confirm_teacher_data(self):
        """Confirm the teacher data and save it to the database."""
        fullname = self.fullname.get().strip().title()
        username = self.username.get().strip().lower()
        password = self.password
        department = self.department.get()
        cover_limit = self.cover_limit.get()
        role = "Normal Teacher"
        detected = 0 # Flag to check for empty cells

        # Validate the data
        if not fullname or not username or not department or not cover_limit:
            messagebox.showerror("Error", "All fields are required!")
            return
        
        if not password:
            messagebox.showerror("Error", "Please generate a password")
            return

        if len(fullname.split()) <= 1:
            messagebox.showerror("Error", "Fullname must include atleast first and last name!")
            return

        #check if username ends with "_gfs"
        if not username.endswith("_gfs"):
            messagebox.showerror("Error", "Username must end with '_gfs'!")
            return

        if not username[0].isalpha():
            messagebox.showerror("Error", "Username must start with a letter!")
            return

        # Check if the username already exists
        if database.get_fullname(username):
            messagebox.showerror("Error", "Username already exists!")
            return

        if not re.match(r"^(?!.*\..*\..*)[A-Za-z0-9]+(\.[A-Za-z0-9]+)?$", username.replace("_gfs","")):
            messagebox.showerror("Error", "Start of Username must only include alphanumeric characters and one fullstop")
            return
        
        if not cover_limit.isdigit():
            messagebox.showerror("Error", "Cover limit must be a integer!")
            return

        # Add the lessons to the database
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday"]

        for x in range(4):
            day = self.days[x]
            self.current_timetable = self.timetables[x]
            for i in range(7):
                subject, class_name, substitute = self.get_lesson(i+1)
                if subject == "Empty" or subject == "":
                    detected = 1 # Flag if any subject is empty

        day = "Friday"
        self.current_timetable = self.timetables[4]
        for i in range(5):
            subject, class_name, substitute = self.get_friday_lesson(i+1)
            if subject == "Empty" or subject == "":
                detected = 1 # Flag if any subject is empty

        if detected == 1:
            response = tk.messagebox.askquestion(title="Empty Cells Detected", 
                                                message="Are you sure you want to save these changes?\nAll empty cells will be considered Free",
                                                icon="warning") # Confirms saving with empty cells turning to free by default
            if response == "no":
                detected = 0
                return
        
        # Adds the teacher to the database and stores password as hash keeping no record of the actual password
        database.add_teacher(username, fullname, role, department, 0, cover_limit)
        database.store_password(username, password)

        for x in range(4):
            day = self.days[x]
            self.current_timetable = self.timetables[x]
            for i in range(7):
                subject, class_name, substitute = self.get_lesson(i+1)
                if subject == "Empty" or subject == "" or subject == "Free":
                    subject = "Free" # Set empty subjects to free
                    class_name = ""
                    substitute = ""
                else:
                    substitute = "None" # Set substitute to None
                database.add_lesson(username, day, i+1, subject, class_name, substitute) # Adds lesson to the database
        
        day = "Friday"
        self.current_timetable = self.timetables[4]
        for i in range(5):
            subject, class_name, substitute = self.get_friday_lesson(i+1)
            if subject == "Empty" or subject == "" or subject == "Free":
                subject = "Free"
                class_name = ""
                substitute = ""
            else:
                substitute = "None"

            database.add_lesson(username, day, i+1, subject, class_name, substitute)
        
        self.controller.update_all_timelines()

        # Updates timetable based on role
        if self.controller.current_role == "SLT":
            self.controller.frames[SLTScreen].timetable.update_timetable()
        else:
            self.controller.frames[TeacherScreen].timetable.update_timetable()
    
        self.clear_entries() # Clear all entry fields and timetable after saving

    def clear_entries(self):
        """Clear all entry fields."""
        self.fullname.delete(0, tk.END)
        self.username.delete(0, tk.END)
        self.department.set("")
        self.cover_limit.delete(0, tk.END)
        self.password = None

        # Resets timetables to empty state
        for i in range(4):
            self.timetables[i].tree.delete(*self.timetables[i].tree.get_children())
            self.timetables[i].tree.insert("", "end", values=["Subject"] + ["Empty"] * 7)
            self.timetables[i].tree.insert("", "end", values=["Class"] + ["Empty"] * 7)
            self.timetables[i].tree.insert("", "end", values=["Substitute"] + ["None"] * 7)
        self.timetables[4].tree.delete(*self.timetables[4].tree.get_children())
        self.timetables[4].tree.insert("", "end", values=["Subject"] + ["Empty"] * 5)
        self.timetables[4].tree.insert("", "end", values=["Class"] + ["Empty"] * 5)
        self.timetables[4].tree.insert("", "end", values=["Substitute"] + ["None"] * 5)

        self.counter = 0 # Reset day counter
        self.update_day() # Update display to show the first day

        self.controller.go_back()

class AccessDatabaseScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.accessed_username = None

        tk.Label(self, text="Teacher Database", font=("Times", 20, "bold")).pack(padx=103.5, pady=(15,10))

        back = tk.Button(self, text="Go Back", width=20, height=3, relief="groove",
                  command=lambda: self.controller.go_back())
        back.place(x=0, y=0)

        controller.binder(back)

        # Configures the style for the treeview
        style = ttk.Style()
        style.configure("Treeview", rowheight=30) # Sets row height

        # Create a treeview widget to display teacher data
        self.tree = ttk.Treeview(self, columns=("Fullname", "Username", "View", "Edit", "Delete"), show="headings", style="Treeview", selectmode="none")
        self.tree.heading("Fullname", text="Fullname")  # Column for teacher's full name
        self.tree.heading("Username", text="Username")  # Column for teacher's username
        self.tree.heading("View", text=" ")  # Column for viewing details
        self.tree.heading("Edit", text="Access Details")  # Column for editing details
        self.tree.heading("Delete", text=" ")  # Column for deleting records

        # Sets column widths and alignment
        for col in ("Fullname", "Username"):
            self.tree.column(col, width=200, anchor="center")

        for col in ("View", "Edit", "Delete"):
            self.tree.column(col, width=100, anchor="center")

        # Creates a vertical scrollbar for the Treeview
        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.place(x=755, y=98, relheight=0.707, relwidth=0.02)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Bind mouse click events to the Treeview
        self.tree.bind('<Button-1>', self.on_click)

        max_height = 155 # Maximum height for the Treeview

        # Adjust the height of the Treeview based on its content
        self.tree.bind('<Configure>', lambda e: self.adjust_treeview_height(max_height))
        self.tree.pack(padx=50, pady=(10,0))

        self.update_treeview() # Populates the Treeview with data

    def update_treeview(self):
        """ Updates the Treeview with the latest teacher data"""
        self.tree.delete(*self.tree.get_children())
        for index, teacher in enumerate(database.get_all_teachers()):
            username = teacher[0]
            fullname = teacher[1]

            tag = 'evenrow' if index % 2 == 0 else 'oddrow' # Alternates row colors for better readability and user friendliness

            # Inserts a new row into the Treeview for each teacher
            self.tree.insert("", "end", values=(fullname, username, "View", "Edit", "Delete"), tags=(tag))
        
        # Configure row colors
        self.tree.tag_configure('evenrow', background='#f0f0f0')  # Light gray for even rows
        self.tree.tag_configure('oddrow', background='white')

    def adjust_treeview_height(self, max_height):
        """Adjusts the height of the Treeview to a maximum value"""
        height = self.tree.winfo_height()
        if height > max_height:
            self.tree.configure(height=max_height // 20)
        
    def on_click(self, event):
        """Handles click events on the Treeview"""
        # Prevents interaction with the header and seperator
        if self.tree.identify_region(event.x, event.y) == "heading":
            return "break"

        if self.tree.identify_region(event.x, event.y) == "separator":
            return "break"

        # Checks if a cell was clicked
        if self.tree.identify_region(event.x, event.y) == "cell":
            self.current_item = self.tree.identify_row(event.y)
            self.current_column = self.tree.identify_column(event.x)
            self.current_value = self.tree.set(self.current_item, self.current_column)
            accessed_username = self.tree.set(self.current_item, "#2")
            current_data = AccessedData() # Creates an instance to store accessed data
            current_data.accessed_username = accessed_username # Stores the accessed username

            # Handle different actions based on the clicked cell value
            if self.current_value == "View":
                if self.controller.current_role == 'Admin':
                    self.controller.frames[AdminViewDatabase].update_labels()
                    self.controller.show_frame(AdminViewDatabase)
                else:
                    self.controller.frames[ViewDatabaseScreen].update_labels()
                    self.controller.show_frame(ViewDatabaseScreen)

            elif self.current_value == "Edit":
                if self.controller.current_role == 'Admin':
                    self.controller.frames[AdminEditDatabase].update_entries()
                    self.controller.show_frame(AdminEditDatabase)
                else:
                    self.controller.frames[EditDatabaseScreen].update_entries()
                    self.controller.show_frame(EditDatabaseScreen)

            elif self.current_value == "Delete":
                current_data = AccessedData()
                if current_data.accessed_username == self.controller.current_user:
                    messagebox.showerror("Error", "You cannot delete yourself!")
                else:
                    self.controller.show_frame(DeleteDatabaseScreen)

class AccessedData:
    accessed_username = None # Class variable to store the accessed username
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AccessedData, cls).__new__(cls)
            cls._instance.accessed_username = None
        return cls._instance

class ViewDatabaseScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.counter = 0

        left = tk.Button(self, text="<--", width=10, height=4, relief="groove",
                  command=lambda: self.decrease_counter())
        left.place(x=54, y=230)
        
        right = tk.Button(self, text="-->", width=10, height=4, relief="groove",
                  command=lambda: self.increase_counter())
        right.place(x=670, y=230)

        back = tk.Button(self, text="Go Back", width=20, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        back.place(x=0, y=359)

        controller.binder(left)
        controller.binder(right)
        controller.binder(back)

        self.timetables = {}
        for i in range(4):
            self.timetables[i] = Timetable(self, controller)
            self.timetables[i].Create_Empty_Timetable()
        self.timetables[4] = Timetable(self, controller)
        self.timetables[4].Create_Friday_Timetable()

        self.current_timetable = self.timetables[0]
        self.current_timetable.place(x=130, y=175)

        self.day_label = tk.Label(self, text="Monday", font=("Arial", 16, "bold"))
        self.day_label.place(x=350, y=145)

    def update_labels(self):
        """Updates the labels with the current teacher's information."""
        current_data = AccessedData()

        self.username = current_data.accessed_username
        self.fullname = database.get_fullname(self.username)
        self.department = database.get_subject_department(self.username)
        self.cover_limit = database.get_cover_limit(self.username)

        # Display the teacher's information in labels
        tk.Label(self, text="Teacher Fullname: ", font=("Times", 14)).grid(row=0, column=0, padx=(130, 0), pady=(1,1), sticky="e")
        tk.Label(self, text="Teacher Username: ", font=("Times", 14)).grid(row=1, column=0, padx=(130, 0), sticky="e")
        tk.Label(self, text="Teacher Department: ", font=("Times", 14)).grid(row=2, column=0, padx=(130, 0), sticky="e")
        tk.Label(self, text="Teacher Cover Limit: ", font=("Times", 14)).grid(row=3, column=0, padx=(130, 0), sticky="e")

        # Create frames to display the fetched information
        tk.LabelFrame(self, width=250, height=28, relief="solid").place(x=295, y=1.5)
        tk.Label(self, text=f"{self.fullname}").place(x=300, y=4)
        tk.LabelFrame(self, width=250, height=28, relief="solid").place(x=295, y=30)
        tk.Label(self, text=f"{self.username}").place(x=300, y=33)
        tk.LabelFrame(self, width=250, height=28, relief="solid").place(x=295, y=55.5)
        tk.Label(self, text=f"{self.department}").place(x=300, y=58)
        tk.LabelFrame(self, width=250, height=28, relief="solid").place(x=295, y=80.5)
        tk.Label(self, text=f"{self.cover_limit}").place(x=300, y=83)

        self.updateview_timetable() # Update the timetable display

    def updateview_timetable(self):
        """Updates the timetable display with the current teacher's lessons."""
        current_data = AccessedData()
        self.username = current_data.accessed_username

        # Fetches lessons for each day of the week for the database
        MondayData = database.get_all_lessons(self.username, "Monday")
        TuesdayData = database.get_all_lessons(self.username, "Tuesday")
        WednesdayData = database.get_all_lessons(self.username, "Wednesday")
        ThursdayData = database.get_all_lessons(self.username, "Thursday")
        FridayData = database.get_all_lessons(self.username, "Friday")

        # Extracts lesson details for each day
        self.MondayLessons = [lesson[2] for lesson in MondayData]
        self.MondayClasses = [lesson[3] for lesson in MondayData]
        self.MondaySubstitutes = [lesson[4] for lesson in MondayData]

        self.TuesdayLessons = [lesson[2] for lesson in TuesdayData]
        self.TuesdayClasses = [lesson[3] for lesson in TuesdayData]
        self.TuesdaySubstitutes = [lesson[4] for lesson in TuesdayData]

        self.WednesdayLessons = [lesson[2] for lesson in WednesdayData]
        self.WednesdayClasses = [lesson[3] for lesson in WednesdayData]
        self.WednesdaySubstitutes = [lesson[4] for lesson in WednesdayData]

        self.ThursdayLessons = [lesson[2] for lesson in ThursdayData]
        self.ThursdayClasses = [lesson[3] for lesson in ThursdayData]
        self.ThursdaySubstitutes = [lesson[4] for lesson in ThursdayData]

        self.FridayLessons = [lesson[2] for lesson in FridayData]
        self.FridayClasses = [lesson[3] for lesson in FridayData]
        self.FridaySubstitutes = [lesson[4] for lesson in FridayData]

        # Clears existing entries in the timetables
        for i in range(5):
            self.timetables[i].tree.delete(*self.timetables[i].tree.get_children())

        # Fills the timetables with the fetched lesson data
        self.fillnormal() # Monday to Thursday
        self.fillfriday() # Friday
    
    def fillnormal(self):
        """Fills the first 4 weekday's timetables with lesson data"""
        self.timetables[0].tree.insert("", "end", values=["Subject"] + self.MondayLessons)
        self.timetables[0].tree.insert("", "end", values=["Class"] + self.MondayClasses)
        self.timetables[0].tree.insert("", "end", values=["Substitute"] + self.MondaySubstitutes)
        self.timetables[1].tree.insert("", "end", values=["Subject"] + self.TuesdayLessons)
        self.timetables[1].tree.insert("", "end", values=["Class"] + self.TuesdayClasses)
        self.timetables[1].tree.insert("", "end", values=["Substitute"] + self.TuesdaySubstitutes)
        self.timetables[2].tree.insert("", "end", values=["Subject"] + self.WednesdayLessons)
        self.timetables[2].tree.insert("", "end", values=["Class"] + self.WednesdayClasses)
        self.timetables[2].tree.insert("", "end", values=["Substitute"] + self.WednesdaySubstitutes)
        self.timetables[3].tree.insert("", "end", values=["Subject"] + self.ThursdayLessons)
        self.timetables[3].tree.insert("", "end", values=["Class"] + self.ThursdayClasses)
        self.timetables[3].tree.insert("", "end", values=["Substitute"] + self.ThursdaySubstitutes)

    def fillfriday(self):
        """Fills the Friday timetable with lesson data."""
        self.timetables[4].tree.insert("", "end", values=["Subject"] + self.FridayLessons)
        self.timetables[4].tree.insert("", "end", values=["Class"] + self.FridayClasses)
        self.timetables[4].tree.insert("", "end", values=["Substitute"] + self.FridaySubstitutes)

    def increase_counter(self):
        if self.counter < 4:
            self.counter += 1
            self.update_day()

    def decrease_counter(self):
        if self.counter > 0:
            self.counter -= 1
            self.update_day()

    def update_display(self):
        self.current_timetable.place_forget()
        self.current_timetable = self.timetables[self.counter]
        if self.counter == 4:  # If it's Friday
            self.current_timetable.place(x=190, y=175)
        else:
            self.current_timetable.place(x=130, y=175)

    def update_day(self):
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.update_daylabel(self.days[self.counter])
        self.update_display()

    def update_daylabel(self, day):
        """Updates the day label"""
        self.day_label.config(text=f"{day}")

    def clear_entries(self):
        self.counter = 0
        self.update_day()

        self.controller.show_frame(AccessDatabaseScreen)

class EditDatabaseScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.counter = 0
        self.password = None
        self.changed = False

        department_list = ["Mathematics", "English", "Science", "History", "Geography", "MFL", "Art", "Music", "PE", "CS"]

        tk.Label(self, text="Teacher Fullname: ", font=("Times", 14)).grid(row=0, column=0, padx=(130, 0), sticky="e")
        self.fullname = tk.Entry(self, width=50)
        self.fullname.grid(row=0, column=1, sticky="w")

        tk.Label(self, text="Teacher Username: ", font=("Times", 14)).grid(row=1, column=0, padx=(130, 0), sticky="e")    
        self.username = tk.Entry(self, width=50)
        self.username.grid(row=1, column=1, sticky="w")

        tk.Label(self, text="Teacher Password: ", font=("Times", 14)).grid(row=2, column=0, padx=(130, 0), sticky="e")

        reset = tk.Button(self, text="Reset Password", width=42, height=1, relief="groove",
                  command=lambda: self.randomize_password())
        reset.grid(row=2, column=1, sticky="w")

        tk.Label(self, text="Teacher Department: ", font=("Times", 14)).grid(row=3, column=0, padx=(130, 0), sticky="e")  
        self.department = ttk.Combobox(self, values=department_list, width=50, state="readonly")
        self.department.grid(row=3, column=1, sticky="w")

        tk.Label(self, text="Cover Limit: ", font=("Times", 14)).grid(row=4, column=0, padx=(130, 0), sticky="e")   
        self.cover_limit = tk.Entry(self, width=50)
        self.cover_limit.grid(row=4, column=1, sticky="w")

        tk.Label(self, text="*Double click a cell to edit", font=("Times", 8, "bold")).grid(row=5, column=0, padx=(130, 0),pady=(15,4), sticky="sw")
        tk.Label(self, text="*Only edit cells with lessons\nLessons left as empty will be considered free", font=("Times", 8, "bold")).place(x=500, y=140)

        left = tk.Button(self, text="<--", width=10, height=4, relief="groove",
                  command=lambda: self.decrease_counter())
        left.place(x=54, y=230)
        
        right = tk.Button(self, text="-->", width=10, height=4, relief="groove",
                  command=lambda: self.increase_counter())
        right.place(x=670, y=230)
        
        cancel = tk.Button(self, text="Cancel", width=20, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        cancel.place(x=0, y=359)
        
        confirm = tk.Button(self, text="Confirm Data", width=20, height=2, relief="groove",
                  command=lambda: self.confirm_teacher_data())
        confirm.place(x=650, y=359)
        
        controller.binder(reset)
        controller.binder(left)
        controller.binder(right)
        controller.binder(cancel)
        controller.binder(confirm)
        
        self.timetables = {}
        for i in range(4):
            self.timetables[i] = Timetable(self, controller)
            self.timetables[i].Create_Empty_Timetable()
        self.timetables[4] = Timetable(self, controller)
        self.timetables[4].Create_Friday_Timetable()

        self.current_timetable = self.timetables[0]
        self.current_timetable.place(x=130, y=175)

        self.day_label = tk.Label(self, text="Monday", font=("Arial", 16, "bold"))
        self.day_label.place(x=350, y=145)

    def update_entries(self):
        """Updates the entry fields with the current teacher's data for editing."""
        current_data = AccessedData()
        self.edit_username = current_data.accessed_username
        self.edit_fullname = database.get_fullname(self.edit_username)
        self.edit_department = database.get_subject_department(self.edit_username)
        self.edit_cover_limit = database.get_cover_limit(self.edit_username)
        
        # Inserts the data into the entry boxes
        self.fullname.insert(0, f"{self.edit_fullname}")
        self.username.insert(0, f"{self.edit_username}")
        self.department.set(f"{self.edit_department}")
        self.cover_limit.insert(0, f"{self.edit_cover_limit}")

        self.updateview_timetable()

    def updateview_timetable(self):
        """Updates the timetable display with the current teacher's lessons."""
        current_data = AccessedData() # Creates an instance to access the accessed username
        self.edit_username = current_data.accessed_username

        # Fetches lessons for each day of the week from the database 
        MondayData = database.get_all_lessons(self.edit_username, "Monday")
        TuesdayData = database.get_all_lessons(self.edit_username, "Tuesday")
        WednesdayData = database.get_all_lessons(self.edit_username, "Wednesday")
        ThursdayData = database.get_all_lessons(self.edit_username, "Thursday")
        FridayData = database.get_all_lessons(self.edit_username, "Friday")

        # Extracts lesson details for each day
        MondayLessons = [lesson[2] for lesson in MondayData]
        MondayClasses = [lesson[3] for lesson in MondayData]
        MondaySubstitutes = [lesson[4] for lesson in MondayData]

        TuesdayLessons = [lesson[2] for lesson in TuesdayData]
        TuesdayClasses = [lesson[3] for lesson in TuesdayData]
        TuesdaySubstitutes = [lesson[4] for lesson in TuesdayData]

        WednesdayLessons = [lesson[2] for lesson in WednesdayData]
        WednesdayClasses = [lesson[3] for lesson in WednesdayData]
        WednesdaySubstitutes = [lesson[4] for lesson in WednesdayData]

        ThursdayLessons = [lesson[2] for lesson in ThursdayData]
        ThursdayClasses = [lesson[3] for lesson in ThursdayData]    
        ThursdaySubstitutes = [lesson[4] for lesson in ThursdayData]

        FridayLessons = [lesson[2] for lesson in FridayData]
        FridayClasses = [lesson[3] for lesson in FridayData]
        FridaySubstitutes = [lesson[4] for lesson in FridayData]

        # Clear existing entries in the timetables
        for i in range(5):
            self.timetables[i].tree.delete(*self.timetables[i].tree.get_children())

        # Fill the timetables with the fetched lesson data
        self.timetables[0].tree.insert("", "end", values=["Subject"] + MondayLessons)
        self.timetables[0].tree.insert("", "end", values=["Class"] + MondayClasses)
        self.timetables[0].tree.insert("", "end", values=["Substitute"] + MondaySubstitutes)
        self.timetables[1].tree.insert("", "end", values=["Subject"] + TuesdayLessons)
        self.timetables[1].tree.insert("", "end", values=["Class"] + TuesdayClasses)
        self.timetables[1].tree.insert("", "end", values=["Substitute"] + TuesdaySubstitutes)
        self.timetables[2].tree.insert("", "end", values=["Subject"] + WednesdayLessons)
        self.timetables[2].tree.insert("", "end", values=["Class"] + WednesdayClasses)
        self.timetables[2].tree.insert("", "end", values=["Substitute"] + WednesdaySubstitutes)
        self.timetables[3].tree.insert("", "end", values=["Subject"] + ThursdayLessons)
        self.timetables[3].tree.insert("", "end", values=["Class"] + ThursdayClasses)
        self.timetables[3].tree.insert("", "end", values=["Substitute"] + ThursdaySubstitutes)
        self.timetables[4].tree.insert("", "end", values=["Subject"] + FridayLessons)
        self.timetables[4].tree.insert("", "end", values=["Class"] + FridayClasses)
        self.timetables[4].tree.insert("", "end", values=["Substitute"] + FridaySubstitutes)

    def get_lesson(self, column):
        values = []
        for item in self.current_timetable.tree.get_children():
            value = self.current_timetable.tree.item(item)['values'][column]
            values.append(value)
        return values

    def get_friday_lesson(self, column):
        # Get all three rows directly
        rows = self.current_timetable.tree.get_children()
        
        # Get values from specific column for each row
        subject = self.current_timetable.tree.item(rows[0])['values'][column]
        class_name = self.current_timetable.tree.item(rows[1])['values'][column]
        substitute = self.current_timetable.tree.item(rows[2])['values'][column]
        values = [subject, class_name, substitute]
        
        return values
    
    def increase_counter(self):
        if self.counter < 4:
            self.counter += 1
            self.update_day()

    def decrease_counter(self):
        if self.counter > 0:
            self.counter -= 1
            self.update_day()

    def update_display(self):
        self.current_timetable.place_forget()
        self.current_timetable = self.timetables[self.counter]
        if self.counter == 4:  # If it's Friday
            self.current_timetable.place(x=190, y=175)
        else:
            self.current_timetable.place(x=130, y=175)

    def update_day(self):
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.update_daylabel(self.days[self.counter])
        self.update_display()
    
    def update_daylabel(self, day):
        """Updates the day label"""
        self.day_label.config(text=f"{day}")

    def randomize_password(self):

        s1 = list(string.ascii_lowercase)
        s2 = list(string.ascii_uppercase)
        s3 = list("@$!%*?_&")
        s4 = list(string.digits)

        random.shuffle(s1)
        random.shuffle(s2)
        random.shuffle(s3)
        random.shuffle(s4)

        result = []

        for x in range(3):
            result.append(s1[x])
            result.append(s2[x])
        
        for x in range(2):
            result.append(s3[x])
            result.append(s4[x])
        
        random.shuffle(result)

        password = "".join(result)
        self.changed = True
        self.password = password
        
        messagebox.showinfo("Password Reset", f"The new password is {password}")
        
    def confirm_teacher_data(self):
        fullname = self.fullname.get().strip().title()
        username = self.username.get().strip().lower()
        password = self.password
        department = self.department.get().strip()
        current_covers = database.get_current_covers(username)
        cover_limit = self.cover_limit.get().strip()
        role = database.get_role(username)
        detected = 0

        database.delete_teacher_data(self.edit_username)
        database.delete_teacher_user(self.edit_username)

        if not fullname or not username or not department or not cover_limit:
            messagebox.showerror("Error", "All fields are required!")
            return

        if len(fullname.split()) <= 1:
            messagebox.showerror("Error", "Fullname must include atleast first and last name!")
            return
        
        #check if username ends with "_gfs"
        if not username.endswith("_gfs"):
            messagebox.showerror("Error", "Username must end with '_gfs'!")
            return

        if not username[0].isalpha():
            messagebox.showerror("Error", "Username must start with a letter!")
            return
        
        if database.get_fullname(username):
            messagebox.showerror("Error", "Username already exists!")
            return
        
        if not re.match(r"^(?!.*\..*\..*)[A-Za-z0-9]+(\.[A-Za-z0-9]+)?$", username.replace("_gfs","")):
            messagebox.showerror("Error", "Start of Username must only include alphanumeric characters and one fullstop")
            return
        
        if not cover_limit.isdigit():
            messagebox.showerror("Error", "Cover limit must be a integer!")
            return
        
        database.add_teacher(username, fullname, role, department, current_covers, cover_limit)

        if self.changed == True:
            database.delete_password(username)
            database.store_password(username, password)

        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday"]

        for x in range(4):
            day = self.days[x]
            self.current_timetable = self.timetables[x]
            for i in range(7):
                subject, class_name, substitute = self.get_lesson(i+1)
                if subject == "Empty" or subject == "":
                    detected = 1

        day = "Friday"
        self.current_timetable = self.timetables[4]
        for i in range(5):
            subject, class_name, substitute = self.get_friday_lesson(i+1)
            if subject == "Empty" or subject == "":
                detected = 1

        if detected == 1:
            response = tk.messagebox.askquestion(title="Empty Cells Detected", 
                                                message="Are you sure you want to save these changes?\nAll empty cells will be considered Free",
                                                icon="warning")
            if response == "no":
                detected = 0
                return

        for x in range(4):
            day = self.days[x]
            self.current_timetable = self.timetables[x]
            for i in range(7):
                subject, class_name, substitute = self.get_lesson(i+1)
                if subject == "Empty" or subject == "" or subject == "Free":
                    subject = "Free"
                    class_name = ""
                    substitute = ""
                else:
                    substitute = "None"
                database.add_lesson(username, day, i+1, subject, class_name, substitute)

        day = "Friday"
        self.current_timetable = self.timetables[4]
        for i in range(5):
            subject, class_name, substitute = self.get_friday_lesson(i+1)
            if subject == "Empty" or subject == "" or subject == "Free":
                subject = "Free"
                class_name = ""
                substitute = ""
            else:
                substitute = "None"
            database.add_lesson(username, day, i+1, subject, class_name, substitute)

        self.controller.update_all_timelines()
        self.controller.frames[AccessDatabaseScreen].update_treeview() 
        self.controller.frames[ViewDatabaseScreen].update_labels()
        self.controller.frames[AdminViewDatabase].update_labels()   
        self.controller.frames[SLTAbsenceConfirmation].update_absent_teachers()

        if self.controller.current_role == "SLT":
            self.controller.frames[SLTScreen].timetable.update_timetable()
        else:
            self.controller.frames[TeacherScreen].timetable.update_timetable()

        self.clear_entries()
    
    def clear_entries(self):
        self.fullname.delete(0, tk.END)
        self.username.delete(0, tk.END)
        self.department.set("")
        self.cover_limit.delete(0, tk.END)
        self.password = None

        self.changed = False
        self.counter = 0
        self.update_day()

        self.controller.show_frame(AccessDatabaseScreen)

class DeleteDatabaseScreen(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Title label for the delete confirmation screen
        tk.Label(self, text="Are you sure?\nThis teacher's data will be\npermanently deleted!", font=("Times", 16, "bold")).place(x=285, y=50)

        # Back, and Delete buttons
        back = tk.Button(self, text="Go Back", width=30, height=4, relief="groove",
                  command=lambda: self.controller.show_frame(AccessDatabaseScreen))
        back.place(x=485, y=220)

        delete = tk.Button(self, text="Delete", width=30, height=4, relief="groove",
                  command=lambda: self.delete_teacher())
        delete.place(x=100, y=220)

        # Binds buttons for hover effects
        controller.binder(back)
        controller.binder(delete)
    
    def delete_teacher(self):
        """Deletes the teacher's data from the database"""
        current_data = AccessedData()
        database.delete_teacher_data(current_data.accessed_username)
        database.delete_teacher_user(current_data.accessed_username)
        database.delete_password(current_data.accessed_username)

        # Updates all timelines in the program to reflect the deletion
        self.controller.update_all_timelines()
        self.controller.frames[AccessDatabaseScreen].update_treeview() 
        self.controller.frames[ViewDatabaseScreen].update_labels()
        self.controller.frames[AdminViewDatabase].update_labels()   
        self.controller.frames[SLTAbsenceConfirmation].update_absent_teachers()

        self.controller.show_frame(AccessDatabaseScreen) # Raises the AccessDatabase screen

class AdminViewDatabase(tk.Frame): # Similar to ViewDatabase but with viewing access of additional variables
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.counter = 0

        left = tk.Button(self, text="<--", width=10, height=4, relief="groove",
                  command=lambda: self.decrease_counter())
        left.place(x=54, y=230)
        
        right = tk.Button(self, text="-->", width=10, height=4, relief="groove",
                  command=lambda: self.increase_counter())
        right.place(x=670, y=230)

        back = tk.Button(self, text="Go Back", width=20, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        back.place(x=0, y=359)

        controller.binder(left)
        controller.binder(right)
        controller.binder(back)

        self.timetables = {}
        for i in range(4):
            self.timetables[i] = Timetable(self, controller)
            self.timetables[i].Create_Empty_Timetable()
        self.timetables[4] = Timetable(self, controller)
        self.timetables[4].Create_Friday_Timetable()

        self.current_timetable = self.timetables[0]
        self.current_timetable.place(x=130, y=175)

        self.day_label = tk.Label(self, text="Monday", font=("Arial", 16, "bold"))
        self.day_label.place(x=350, y=145)

    def update_labels(self):
        current_data = AccessedData()

        self.username = current_data.accessed_username
        self.fullname = database.get_fullname(self.username)
        self.department = database.get_subject_department(self.username)
        self.current_covers = database.get_current_covers(self.username)
        self.cover_limit = database.get_cover_limit(self.username)
        self.role = database.get_role(self.username)

        tk.Label(self, text="Teacher Fullname: ", font=("Times", 14)).grid(row=0, column=0, padx=(10, 0), pady=(1,1), sticky="e")
        tk.Label(self, text="Teacher Username: ", font=("Times", 14)).grid(row=1, column=0, padx=(10, 0), sticky="e")
        tk.Label(self, text="Teacher Department: ", font=("Times", 14)).grid(row=2, column=0, padx=(10, 0), sticky="e")
        tk.Label(self, text="Teacher Current Covers: ", font=("Times", 14)).grid(row=0, column=2, padx=(205, 0), sticky="e")
        tk.Label(self, text="Teacher  Cover Limit: ", font=("Times", 14)).grid(row=1, column=2, padx=(205, 0), sticky="e")
        tk.Label(self, text="Role: ", font=("Times", 14)).grid(row=2, column=2, padx=(205, 0), sticky="e")

        tk.LabelFrame(self, width=200, height=28, relief="solid").place(x=180, y=1.5)
        tk.Label(self, text=f"{self.fullname}").place(x=185, y=4)
        tk.LabelFrame(self, width=200, height=28, relief="solid").place(x=180, y=30)
        tk.Label(self, text=f"{self.username}").place(x=185, y=32)
        tk.LabelFrame(self, width=200, height=28, relief="solid").place(x=180, y=55.5)
        tk.Label(self, text=f"{self.department}").place(x=185, y=58)
        tk.LabelFrame(self, width=200, height=28, relief="solid").place(x=575, y=1.5)
        tk.Label(self, text=f"{self.current_covers}").place(x=580, y=4)
        tk.LabelFrame(self, width=200, height=28, relief="solid").place(x=575, y=30)
        tk.Label(self, text=f"{self.cover_limit}").place(x=580, y=32)
        tk.LabelFrame(self, width=200, height=28, relief="solid").place(x=575, y=55.5)
        tk.Label(self, text=f"{self.role}").place(x=580, y=58)

        self.updateview_timetable()

    def updateview_timetable(self):
        current_data = AccessedData()
        self.username = current_data.accessed_username

        MondayData = database.get_all_lessons(self.username, "Monday")
        TuesdayData = database.get_all_lessons(self.username, "Tuesday")
        WednesdayData = database.get_all_lessons(self.username, "Wednesday")
        ThursdayData = database.get_all_lessons(self.username, "Thursday")
        FridayData = database.get_all_lessons(self.username, "Friday")

        self.MondayLessons = [lesson[2] for lesson in MondayData]
        self.MondayClasses = [lesson[3] for lesson in MondayData]
        self.MondaySubstitutes = [lesson[4] for lesson in MondayData]

        self.TuesdayLessons = [lesson[2] for lesson in TuesdayData]
        self.TuesdayClasses = [lesson[3] for lesson in TuesdayData]
        self.TuesdaySubstitutes = [lesson[4] for lesson in TuesdayData]

        self.WednesdayLessons = [lesson[2] for lesson in WednesdayData]
        self.WednesdayClasses = [lesson[3] for lesson in WednesdayData]
        self.WednesdaySubstitutes = [lesson[4] for lesson in WednesdayData]

        self.ThursdayLessons = [lesson[2] for lesson in ThursdayData]
        self.ThursdayClasses = [lesson[3] for lesson in ThursdayData]
        self.ThursdaySubstitutes = [lesson[4] for lesson in ThursdayData]

        self.FridayLessons = [lesson[2] for lesson in FridayData]
        self.FridayClasses = [lesson[3] for lesson in FridayData]
        self.FridaySubstitutes = [lesson[4] for lesson in FridayData]

        for i in range(5):
            self.timetables[i].tree.delete(*self.timetables[i].tree.get_children())

        self.fillnormal()
        self.fillfriday()
    
    def fillnormal(self):
        self.timetables[0].tree.insert("", "end", values=["Subject"] + self.MondayLessons)
        self.timetables[0].tree.insert("", "end", values=["Class"] + self.MondayClasses)
        self.timetables[0].tree.insert("", "end", values=["Substitute"] + self.MondaySubstitutes)
        self.timetables[1].tree.insert("", "end", values=["Subject"] + self.TuesdayLessons)
        self.timetables[1].tree.insert("", "end", values=["Class"] + self.TuesdayClasses)
        self.timetables[1].tree.insert("", "end", values=["Substitute"] + self.TuesdaySubstitutes)
        self.timetables[2].tree.insert("", "end", values=["Subject"] + self.WednesdayLessons)
        self.timetables[2].tree.insert("", "end", values=["Class"] + self.WednesdayClasses)
        self.timetables[2].tree.insert("", "end", values=["Substitute"] + self.WednesdaySubstitutes)
        self.timetables[3].tree.insert("", "end", values=["Subject"] + self.ThursdayLessons)
        self.timetables[3].tree.insert("", "end", values=["Class"] + self.ThursdayClasses)
        self.timetables[3].tree.insert("", "end", values=["Substitute"] + self.ThursdaySubstitutes)

    def fillfriday(self):
        self.timetables[4].tree.insert("", "end", values=["Subject"] + self.FridayLessons)
        self.timetables[4].tree.insert("", "end", values=["Class"] + self.FridayClasses)
        self.timetables[4].tree.insert("", "end", values=["Substitute"] + self.FridaySubstitutes)

    def increase_counter(self):
        if self.counter < 4:
            self.counter += 1
            self.update_day()

    def decrease_counter(self):
        if self.counter > 0:
            self.counter -= 1
            self.update_day()

    def update_display(self):
        self.current_timetable.place_forget()
        self.current_timetable = self.timetables[self.counter]
        if self.counter == 4:  # If it's Friday
            self.current_timetable.place(x=190, y=175)
        else:
            self.current_timetable.place(x=130, y=175)

    def update_day(self):
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.update_daylabel(self.days[self.counter])
        self.update_display()

    def update_daylabel(self, day):
        """Updates the day label"""
        self.day_label.config(text=f"{day}")

    def clear_entries(self):
        self.counter = 0
        self.update_day()

        self.controller.show_frame(AccessDatabaseScreen)

class AdminEditDatabase(tk.Frame): # Similar to EditDatabase but with editing access of additional variables
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller
        self.counter = 0
        self.password = None
        self.changed = False

        department_list = ["Mathematics", "English", "Science", "History", "Geography", "MFL", "Art", "Music", "PE", "CS"]

        tk.Label(self, text="Teacher Fullname: ", font=("Times", 14)).grid(row=0, column=0, padx=(15, 0), pady=(20, 0), sticky="e")
        self.fullname = tk.Entry(self, width=30)
        self.fullname.grid(row=0, column=1, padx=(5, 0), pady=(20, 0), sticky="w")

        tk.Label(self, text="Teacher Username: ", font=("Times", 14)).grid(row=1, column=0, padx=(15, 0), sticky="e")    
        self.username = tk.Entry(self, width=30)
        self.username.grid(row=1, column=1, padx=(5, 0), sticky="w")

        tk.Label(self, text="Teacher Password: ", font=("Times", 14)).grid(row=2, column=0, padx=(15, 0), sticky="e")

        reset = tk.Button(self, text="Reset Password", width=25, height=1, relief="groove",
                  command=lambda: self.randomize_password())
        reset.grid(row=2, column=1, padx=(5, 0), sticky="w")

        tk.Label(self, text="Teacher Department: ", font=("Times", 14)).grid(row=0, column=2, padx=(30, 0), pady=(20, 0), sticky="e")  
        self.department = ttk.Combobox(self, values=department_list, width=30, state="readonly")
        self.department.grid(row=0, column=3, padx=(5, 15), pady=(20, 0), sticky="w")

        tk.Label(self, text="Current Covers: ", font=("Times", 14)).grid(row=1, column=2, padx=(30, 0), sticky="e")  
        self.current_covers = tk.Entry(self, width=30)
        self.current_covers.grid(row=1, column=3, padx=(5, 15), sticky="w")

        tk.Label(self, text="Cover Limit: ", font=("Times", 14)).grid(row=2, column=2, padx=(30, 0), sticky="e")   
        self.cover_limit = tk.Entry(self, width=30)
        self.cover_limit.grid(row=2, column=3, padx=(5, 15), sticky="w")

        tk.Label(self, text="Teacher Role: ", font=("Times", 14)).place(x=535, y=110)
        self.role = ttk.Combobox(self, values=["SLT", "Normal Teacher"], width=15, state="readonly")
        self.role.place(x=650, y=112)

        tk.Label(self, text="*Double click a cell to edit", font=("Times", 8, "bold")).place(x=135, y=150)
        tk.Label(self, text="*Only edit cells with lessons\nLessons left as empty will be considered free", font=("Times", 8, "bold")).place(x=500, y=140)

        left = tk.Button(self, text="<--", width=10, height=4, relief="groove",
                  command=lambda: self.decrease_counter())
        left.place(x=54, y=230)
        
        right = tk.Button(self, text="-->", width=10, height=4, relief="groove",
                  command=lambda: self.increase_counter())
        right.place(x=670, y=230)
        
        cancel = tk.Button(self, text="Cancel", width=20, height=2, relief="groove",
                  command=lambda: self.clear_entries())
        cancel.place(x=0, y=359)
        
        confirm = tk.Button(self, text="Confirm Data", width=20, height=2, relief="groove",
                  command=lambda: self.confirm_teacher_data())
        confirm.place(x=650, y=359)
        
        controller.binder(reset)
        controller.binder(left)
        controller.binder(right)
        controller.binder(cancel)
        controller.binder(confirm)
        
        self.timetables = {}
        for i in range(4):
            self.timetables[i] = Timetable(self, controller)
            self.timetables[i].Create_Empty_Timetable()
        self.timetables[4] = Timetable(self, controller)
        self.timetables[4].Create_Friday_Timetable()

        self.current_timetable = self.timetables[0]
        self.current_timetable.place(x=130, y=175)

        self.day_label = tk.Label(self, text="Monday", font=("Arial", 16, "bold"))
        self.day_label.place(x=350, y=145)

    def update_entries(self):
        current_data = AccessedData()
        self.edit_username = current_data.accessed_username
        self.edit_fullname = database.get_fullname(self.edit_username)
        self.edit_department = database.get_subject_department(self.edit_username)
        self.edit_current_covers = database.get_current_covers(self.edit_username)
        self.edit_cover_limit = database.get_cover_limit(self.edit_username)
        self.edit_role = database.get_role(self.edit_username)
        
        self.fullname.insert(0, f"{self.edit_fullname}")
        self.username.insert(0, f"{self.edit_username}")
        self.department.set(f"{self.edit_department}")
        self.current_covers.insert(0, f"{self.edit_current_covers}")
        self.cover_limit.insert(0, f"{self.edit_cover_limit}")
        self.role.set(f"{self.edit_role}")

        self.updateview_timetable()

    def updateview_timetable(self):
        current_data = AccessedData()
        self.edit_username = current_data.accessed_username

        MondayData = database.get_all_lessons(self.edit_username, "Monday")
        TuesdayData = database.get_all_lessons(self.edit_username, "Tuesday")
        WednesdayData = database.get_all_lessons(self.edit_username, "Wednesday")
        ThursdayData = database.get_all_lessons(self.edit_username, "Thursday")
        FridayData = database.get_all_lessons(self.edit_username, "Friday")

        MondayLessons = [lesson[2] for lesson in MondayData]
        MondayClasses = [lesson[3] for lesson in MondayData]
        MondaySubstitutes = [lesson[4] for lesson in MondayData]

        TuesdayLessons = [lesson[2] for lesson in TuesdayData]
        TuesdayClasses = [lesson[3] for lesson in TuesdayData]
        TuesdaySubstitutes = [lesson[4] for lesson in TuesdayData]

        WednesdayLessons = [lesson[2] for lesson in WednesdayData]
        WednesdayClasses = [lesson[3] for lesson in WednesdayData]
        WednesdaySubstitutes = [lesson[4] for lesson in WednesdayData]

        ThursdayLessons = [lesson[2] for lesson in ThursdayData]
        ThursdayClasses = [lesson[3] for lesson in ThursdayData]    
        ThursdaySubstitutes = [lesson[4] for lesson in ThursdayData]

        FridayLessons = [lesson[2] for lesson in FridayData]
        FridayClasses = [lesson[3] for lesson in FridayData]
        FridaySubstitutes = [lesson[4] for lesson in FridayData]

        for i in range(5):
            self.timetables[i].tree.delete(*self.timetables[i].tree.get_children())

        self.timetables[0].tree.insert("", "end", values=["Subject"] + MondayLessons)
        self.timetables[0].tree.insert("", "end", values=["Class"] + MondayClasses)
        self.timetables[0].tree.insert("", "end", values=["Substitute"] + MondaySubstitutes)
        self.timetables[1].tree.insert("", "end", values=["Subject"] + TuesdayLessons)
        self.timetables[1].tree.insert("", "end", values=["Class"] + TuesdayClasses)
        self.timetables[1].tree.insert("", "end", values=["Substitute"] + TuesdaySubstitutes)
        self.timetables[2].tree.insert("", "end", values=["Subject"] + WednesdayLessons)
        self.timetables[2].tree.insert("", "end", values=["Class"] + WednesdayClasses)
        self.timetables[2].tree.insert("", "end", values=["Substitute"] + WednesdaySubstitutes)
        self.timetables[3].tree.insert("", "end", values=["Subject"] + ThursdayLessons)
        self.timetables[3].tree.insert("", "end", values=["Class"] + ThursdayClasses)
        self.timetables[3].tree.insert("", "end", values=["Substitute"] + ThursdaySubstitutes)
        self.timetables[4].tree.insert("", "end", values=["Subject"] + FridayLessons)
        self.timetables[4].tree.insert("", "end", values=["Class"] + FridayClasses)
        self.timetables[4].tree.insert("", "end", values=["Substitute"] + FridaySubstitutes)

    def get_lesson(self, column):
        values = []
        for item in self.current_timetable.tree.get_children():
            value = self.current_timetable.tree.item(item)['values'][column]
            values.append(value)
        return values

    def get_friday_lesson(self, column):
        # Get all three rows directly
        rows = self.current_timetable.tree.get_children()
        
        # Get values from specific column for each row
        subject = self.current_timetable.tree.item(rows[0])['values'][column]
        class_name = self.current_timetable.tree.item(rows[1])['values'][column]
        substitute = self.current_timetable.tree.item(rows[2])['values'][column]
        values = [subject, class_name, substitute]
        
        return values
    
    def increase_counter(self):
        if self.counter < 4:
            self.counter += 1
            self.update_day()

    def decrease_counter(self):
        if self.counter > 0:
            self.counter -= 1
            self.update_day()

    def update_display(self):
        self.current_timetable.place_forget()
        self.current_timetable = self.timetables[self.counter]
        if self.counter == 4:  # If it's Friday
            self.current_timetable.place(x=190, y=175)
        else:
            self.current_timetable.place(x=130, y=175)

    def update_day(self):
        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        self.update_daylabel(self.days[self.counter])
        self.update_display()
    
    def update_daylabel(self, day):
        """Updates the day label"""
        self.day_label.config(text=f"{day}")

    def randomize_password(self):

        s1 = list(string.ascii_lowercase)
        s2 = list(string.ascii_uppercase)
        s3 = list("@$!%*?_&")
        s4 = list(string.digits)

        random.shuffle(s1)
        random.shuffle(s2)
        random.shuffle(s3)
        random.shuffle(s4)

        result = []

        for x in range(3):
            result.append(s1[x])
            result.append(s2[x])
        
        for x in range(2):
            result.append(s3[x])
            result.append(s4[x])
        
        random.shuffle(result)

        password = "".join(result)
        self.changed = True
        self.password = password
        
        messagebox.showinfo("Password Reset", f"The new password is {password}")
        
    def confirm_teacher_data(self):
        fullname = self.fullname.get().strip().title()
        username = self.username.get().strip().lower()
        password = self.password
        department = self.department.get().strip()
        current_covers = self.current_covers.get().strip()
        cover_limit = self.cover_limit.get().strip()
        role = self.role.get().strip()
        detected = 0

        database.delete_teacher_data(self.edit_username)
        database.delete_teacher_user(self.edit_username)

        if not fullname or not username or not department or not current_covers or not role or not cover_limit:
            messagebox.showerror("Error", "All fields are required!")
            return
        
        if len(fullname.split()) <= 1:
            messagebox.showerror("Error", "Fullname must include atleast first and last name!")
            return

        if not username.endswith("_gfs"):
            messagebox.showerror("Error", "Username must end with '_gfs'!")
            return

        if not username[0].isalpha():
            messagebox.showerror("Error", "Username must start with a letter!")
            return

        if database.get_fullname(username):
            messagebox.showerror("Error", "Username already exists!")
            return

        if not re.match(r"^(?!.*\..*\..*)[A-Za-z0-9]+(\.[A-Za-z0-9]+)?$", username.replace("_gfs","")):
            messagebox.showerror("Error", "Start of Username must only include alphanumeric characters and one fullstop")
            return

        if not current_covers.isdigit():
            messagebox.showerror("Error", "Current Covers must be a integer!")
            return
        
        if not cover_limit.isdigit():
            messagebox.showerror("Error", "Cover limit must be a integer!")
            return

        self.days = ["Monday", "Tuesday", "Wednesday", "Thursday"]

        for x in range(4):
            day = self.days[x]
            self.current_timetable = self.timetables[x]
            for i in range(7):
                subject, class_name, substitute = self.get_lesson(i+1)
                if subject == "Empty":
                    detected = 1

        day = "Friday"
        self.current_timetable = self.timetables[4]
        for i in range(5):
            subject, class_name, substitute = self.get_friday_lesson(i+1)
            if subject == "Empty":
                detected = 1

        if detected == 1:
            response = tk.messagebox.askquestion(title="Empty Cells Detected", 
                                                message="Are you sure you want to save these changes?\nAll empty cells will be considered Free",
                                                icon="warning")
            if response == "no":
                detected = 0
                return
            
        database.add_teacher(username, fullname, role, department, current_covers, cover_limit)
        if self.changed == True:
            database.delete_password(username)
            database.store_password(username, password)

        for x in range(4):
            day = self.days[x]
            self.current_timetable = self.timetables[x]
            for i in range(7):
                subject, class_name, substitute = self.get_lesson(i+1)
                if subject == "Empty" or subject == "" or subject == "Free":
                    subject = "Free"
                    class_name = ""
                    substitute = ""
                else:
                    substitute = "None"
                database.add_lesson(username, day, i+1, subject, class_name, substitute)

        day = "Friday"
        self.current_timetable = self.timetables[4]
        for i in range(5):
            subject, class_name, substitute = self.get_friday_lesson(i+1)
            if subject == "Empty" or subject == "" or subject == "Free":
                subject = "Free"
                class_name = ""
                substitute = ""
            else:
                substitute = "None"
            database.add_lesson(username, day, i+1, subject, class_name, substitute)

        self.controller.update_all_timelines()
        self.controller.frames[AccessDatabaseScreen].update_treeview() 
        self.controller.frames[ViewDatabaseScreen].update_labels()
        self.controller.frames[AdminViewDatabase].update_labels()   
        self.controller.frames[SLTAbsenceConfirmation].update_absent_teachers()

        if self.controller.current_role == "SLT":
            self.controller.frames[SLTScreen].timetable.update_timetable()
        else:
            self.controller.frames[TeacherScreen].timetable.update_timetable()

        self.clear_entries()
    
    def clear_entries(self):
        self.fullname.delete(0, tk.END)
        self.username.delete(0, tk.END)
        self.department.set("")
        self.current_covers.delete(0, tk.END)
        self.cover_limit.delete(0, tk.END)
        self.role.set("")
        self.password = None

        self.changed = False
        self.counter = 0
        self.update_day()

        self.controller.show_frame(AccessDatabaseScreen)

class MainAlgorithm():
    def __init__(self, controller):
        self.controller = controller  # Store reference to MyTimetableApp
        self.date = datetime.datetime.now() # Gets the current data and time
        self.weekday = datetime.datetime.today().strftime('%A') # Gets the current day of the week
        self.AllTeachers = [] # List to store all the teachers
        self.AllTeachers = database.get_all_usernames() # Fetches all usernames from the database
        self.AbsentTeachers = [] # List to store absent teachers
        self.NonAbsentTeachers = [] # List to store teachers that aren't absent
        self.CoverNeedingLessons = [] # List to store lessons that need cover
        self.CoverAllocations = [] # List to store cover allocations

    def cover_allocation(self):
        """Allocates cover for absent teachers based on their lessons."""
        # Identify absent teachers
        for Teacher in self.AllTeachers: # Iterate all the teachers
            if database.is_absent(Teacher, self.date): # Check if they are absent
                self.AbsentTeachers.append(Teacher) # Appends them to the AbsentTeachers list

        self.NonAbsentTeachers = self.AllTeachers

        for Teacher in self.AbsentTeachers: # Iterates all the absent teachers
            self.NonAbsentTeachers.remove(Teacher) # Removes teachers who are absent from the non absent teachers list

        for Teacher in self.AbsentTeachers: # Iterates all the absent teachers
            lessons = database.get_all_lessons(Teacher, self.weekday) # Gets all the lessons of the teacher
            for lesson in lessons: # Iterates all lessons
                if lesson[2] != "Free" and lesson[3] != "" and lesson[4] == "None" and lesson[2] != "Empty": 
                    self.CoverNeedingLessons.append(lesson) # Appends all non free lessons

        for x in range(len(self.CoverNeedingLessons)): # Iterates all cover need lessons
            # Defines absent teacher's info
            absent_teacher = self.CoverNeedingLessons[x][0]
            absent_teacher_name = database.get_fullname(absent_teacher)
            absent_teacher_department = database.get_subject_department(absent_teacher)
            absent_lesson_num = self.CoverNeedingLessons[x][1]
            absent_subject = self.CoverNeedingLessons[x][2]
            absent_class = self.CoverNeedingLessons[x][3]
            FreeTeachers = [] 
            SameDepartmentTeachers = []
            SuitableTeachers = []

            for teacher in self.NonAbsentTeachers: # Iterates all non absent teachers
                lesson = database.get_one_lesson(teacher, self.weekday, absent_lesson_num)
                if lesson[2] == "Free":
                    FreeTeachers.append(teacher) # Appends if they are free during a cover needing lesson
            
            if not FreeTeachers: # Sends an email if there are no free teachers found for a certain cover needing lesson
                self.send_email(absent_teacher_name, absent_lesson_num, absent_subject, absent_class)
                
            else:
                for teacher in FreeTeachers: # Iterates through free teachers
                    department = database.get_subject_department(teacher)
                    if department == absent_teacher_department: # Checks teacher's department against the absent teacher's department
                        SameDepartmentTeachers.append(teacher) # Appends if same department
                
                if not SameDepartmentTeachers: # If there are no same department teachers
                    lowest_cover_percentage = 9999 # Sets lowest percentage to an extremely high amount
                    for teacher in FreeTeachers: # Iterates through free teachers since there are no same department teachers
                        current = database.get_current_covers(teacher) 
                        limit = database.get_cover_limit(teacher)
                        cover_precentage = ( current / limit ) * 100 # Calculates cover percentage using curren covers and cover limit
                        
                        # Iterates to find the teacher with the lowest cover percentage
                        if cover_precentage < lowest_cover_percentage: 
                            lowest_cover_percentage = cover_precentage
                            SuitableTeachers = [teacher]
                        elif cover_precentage == lowest_cover_percentage:
                            SuitableTeachers.append(teacher)

                    selected_teacher = random.choice(SuitableTeachers) # Randomly selects between suitable teachers
                    # Appends the cover allocation list and edits the lessons in the database
                    self.CoverAllocations.append([absent_teacher, selected_teacher, self.weekday, absent_lesson_num, absent_subject, absent_class])
                    database.edit_lesson(selected_teacher, self.weekday, absent_lesson_num, absent_subject, absent_class, f"Subbing\n{absent_teacher_name}")
                    database.edit_lesson(absent_teacher, self.weekday, absent_lesson_num, absent_subject, absent_class, f"Subbed\nby {selected_teacher[0]}")

                    database.increment_current_covers(selected_teacher) # Increments the current covers

                else:
                    # Iterates similarly based on cover percentage but for same department teachers
                    lowest_cover_percentage = 999
                    for teacher in SameDepartmentTeachers:
                        current = database.get_current_covers(teacher)
                        limit = database.get_cover_limit(teacher)
                        cover_precentage = ( current / limit ) * 100

                        if cover_precentage < lowest_cover_percentage:
                            lowest_cover_percentage = cover_precentage
                            SuitableTeachers = [teacher]
                        elif cover_precentage == lowest_cover_percentage:
                            SuitableTeachers.append(teacher)

                    selected_teacher = random.choice(SuitableTeachers)
                    self.CoverAllocations.append([absent_teacher, selected_teacher, self.weekday, absent_lesson_num, absent_subject, absent_class])
                    database.edit_lesson(selected_teacher, self.weekday, absent_lesson_num, absent_subject, absent_class, f"Subbing\n{absent_teacher_name}")
                    database.edit_lesson(absent_teacher, self.weekday, absent_lesson_num, absent_subject, absent_class, f"Subbed\nby {selected_teacher[0]}")

                    database.increment_current_covers(selected_teacher)
        
        #Refresh the entire timetable UI
        self.controller.frames[SLTScreen].timetable.update_timetable()
        self.controller.frames[TeacherScreen].timetable.update_timetable()
        self.controller.frames[AccessDatabaseScreen].update_treeview() 
        self.controller.frames[ViewDatabaseScreen].update_labels()
        self.controller.frames[AdminViewDatabase].update_labels()   
        self.controller.frames[SLTAbsenceConfirmation].update_absent_teachers()
    
    def revert_covers(self):
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        for teacher in self.AllTeachers: # Iterates all the teachers
            for x in range(5):
                lessons = database.get_all_lessons(teacher, days[x])

                for lesson in lessons: # Iterates all lessons
                    if lesson[4] != "None":
                        if lesson[4].startswith("Subbing"): # If teacher used to be substituting a lesson it returns to a free lesson
                            lesson_num = lesson[1]
                            subject = "Free"
                            class_name = ""
                            substitute = ""
                            database.edit_lesson(teacher, days[x], lesson_num, subject, class_name, substitute)

                        elif lesson[4].startswith("Subbed"): # If teacher was absent and got subbed returns lesson to normal with subsititute as None
                            lesson_num = lesson[1]
                            original = database.get_one_lesson(teacher, days[x], lesson_num)
                            subject = original[2]
                            class_name = original[3]
                            substitute = "None"
                            database.edit_lesson(teacher, days[x], lesson_num, subject, class_name, substitute) 
        
        #Refresh the entire timetable UI
        self.controller.update_all_timelines()  

    def send_email(self, Teacher, Lesson, Subject, Class):
        try:
            email_sender = "cover.allocation@gmail.com"
            email_password = "cluolalrbzzelgzg"
            email_receiver = "clashemara@gmail.com" # Test Email for testing purposes

            Title = f"Issue with Cover Allocation - Action Required, {self.date.strftime('%Y-%m-%d')}"
            Body = f"""
            Dear Saif,
            We were not able to find a cover for the teacher with the following details
            Kindly arrange a substitute

            Today: {self.date.strftime('%Y-%m-%d')},
            Absent Teacher Name : {Teacher}
            Lesson Number : {Lesson}
            Lesson Subject : {Subject}
            Class : {Class}

            Kind Regards,
            Cover Allocation Program
            """

            email = yagmail.SMTP(email_sender, email_password)
            email.send(email_receiver, Title, Body)
            
        except:
            pass

# Tkinter main loop
if __name__ == "__main__":
    database = Database()
    root = tk.Tk()
    app = MyTimetableApp(root)
    root.mainloop()