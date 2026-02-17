# Authentication and Authorization
User
    - Role: Student | Teacher | Admin


# Databases
## ===== auth =======
User:
    Role: student | teacher | admin

Institution:
    Name: str

InstitutionMember:
    Institution: FK(Institution)
    User: FL(User)
    Role: owner | creator | auditor

## ======== course ========
CourseCategory:
    - name: str
    - description: str
Course:
    - name: str
    - image: path
    - offerer_user: FK(User)
    - offerer_institution: FK(Institution)
    - category: FK(CourseCategory)
    - description: str
    - rating: avg(Feedback.rating)
    - status: Published | Draft
    - registered_from: datetime
    - registered_to: datetime

CourseMaterial:
    - deadline: datetime
    - type: video | reading | quiz | discussion
    - content_url: path
    - discussion: FK(DiscussionThread)
    - quiz: FK(Quiz)

DiscussionThread:
    - <need to find out how to structure this extremely nested thread structure>

Quiz:
    course: Course
    content: JSON{
        questions: []{
            id: int
            question: str
            type: multiple_choice | text
            choices: []{
                value: Any
                text: str
            }
        }
    }
    answer: EncryptedJSON{
        answers: []{
            id: int
            answer: Any
        }
    }


Feedback:
    - course: FK(Course)
    - user: FK(User)
    - review: str
    - rating: int 0 <= rat <= 5

# ====== Enrollment =======
Enrollment:
    course: FK(Course)
    user: FK(user)
    status: enrolled | blocked

Progress:
    student: FK(user)
    material: FK(CourseMaterial)
    completed: bool

Submission:
    student: FK(User)
    material: FK(CourseMaterial)
    grade: total percentage
    answer: JSON{
        answers: []{
            id: int,
            value: Any,
            score: float
        }
    }

# ====== Notification =====
Notification:
    message: str
    redirect_to: url

# ====== Status ====
Status:
    user: FK(User)
    text: str
    image_path: path
    video_path: path 

StatusComment:
    status: FK(Status)
    user: FK(user)
    text: str
    

# User stories
### 1.1 Auth(Institution)
    - User can registered and login based according to the role
    - User with teacher role can create institution
    - User with teacher role can invite another teachers to the institution.
### 1.1 Auth(Course)
    - user with teacher role or user with institution member with creator or owner access can create courses
    - user with institution member with auditor can audit the courses
    - user with student role can view course materials
### 2.1 Courses
    - User with teacher can create course and course materials
    - Other user of the same organization can edit the course detail page
    - Student already enrolled will have different course detail page
    - Student can see course material, see the grades, see the discussion threads, see the course mates
    - Teachers can always change the visibility of the course
    - Student can always search courses
### 2.2 Materials
    - Teacher can add course material ranging from reading, video, discussion and quiz
    - Quiz can be graded and answer will be encrypted
    - Student of the course are notified when course material are updated.
### 2.3 Submissions
    - Student can create submission on the course.
    - Submission will be automatically graded if creator added answers in the material
    - Submission will be send to the tutor if creator did not add the answer
    - Tutor can update the grade and publish it
### 2.4 Progress
    - User can mark the progress of the course material.
    - Automatic on quiz submit,  click next btn for video or reading, first discussion submitted on discussion
### 2.4 Rating
    - Student who has completed 30% of the progress has option to leave feedback of the course
### 3.1 Enrollment
    - Student can create enrollment to the course
    - Student can delete enrollment to the course
    - Teacher can delete enrollment to the course
    - Teacher can block enrollment to the course
    - Cannot enroll if registration period is passed.
    - Teacher view all enrollment
### 4.1 Status
    - User can create status post in their profile and other can see them.
    - User of the same course member are notify of the status update of each other.
    - User can comment on the status of another student.
### 5.1 Chat
    - 

# Pages
## HomePage
Student:
    - /student/dashboard
        - attributes:
            - Registered Course
            - Incoming deadline
            - Grades
            - Progress
Teacher:
    - /teacher/dashboard
    - Proctored Courses
    - Incoming deadlines

Status:
    - content
    - reply

Course Explore:
    - /courses
        - attributes:
            - search by name
            - search by offered institution
            - search by category
            - search by rating
    - /course
        - attributes:
            materials

Course Detail:
    - /course/<id>

Profile:
    - profile/<id>

Chat:
    - chat/<id>





# Notes
Each user should have a “home” page that shows their user information and any other
interesting data such as registered courses, upcoming deadlines, etc. It should also
display user status updates. These home pages should be discoverable and visible to
other users. 

This doesn't make sense. Deadlines shouldn't be publicily available and also home page is the place where student or teacher manage their entire study, not for public. For this, I split profile and dashboard. Dashboard is only for owner, can see grades, deadlines, notification and progress and registered course. And profile, public and contain registered course, personal info and status.

# UI Design
/dashboard
    - page for status update, viewing courses, deadline and grades for both student and teacher

/courses
    - page to explore and search courses
/course/new
    - page to create a new course
/course/id
    - page to explore view detail about the new course(un-enrolled)
    - page to view the course material once you enroll(enrolled)
/course/id/overview
    - page to edit general information of the course(teacher)
    - page to leave rating and un-enroll(student)
/course/id/students
    - page to search students and block, remove from course(teacher)
/course/id/instructors
    - page to search teacher and add as instructors(teacher)
/course/id/material/id
    - page to edit course content(teacher)
    - page to view course content and mark as complete(student)

/profile/id
    - page to see and manage status, profile information

/messages/id
    - page to communicate between teacher and student
    - page to create a whiteboard to draw 

# Status file bucket

# User, Profile and Authentication
- Extend abstract user view and add a role field
- Add profile, if no profile is there, user are redirected to profile pate, if not redirect to dashboard on login
- use django forms to clean registered form.
- use image field to store profile image.
- add logout, and configure login/logout redirect url in setting as i am using django default auth classes.
- add edit profile(auth guarded) while view profile is not auth guarded

# Status
- Use model form since there is no processing needed.
- add optional single file updload functionality and creaeted time is added for sorting.
- Use django paginator class to auto-paginate the status in both dashbaord and profile.

# Course
- Course create, just use modelform because it is streightforward.
- Add custom authenticator class to limit access only to student for course create.
- Use is_teacher template tag to demonstrate template tags and hide/display certain UI dependin gon the user role
- Use can_enroll template tag to display/hide enroll button based on role, registration date.

# Enrollment
- To handle block, we add status, if status is block, we don't allow user to access. And duplicated enrollemnts are also rejected
- To handle batch, we add expired at. if enrollment is expired they can refresh the enrollment again. and if not they cannot access course materials.
# Instructor
- Instructor page, only accessible by course owner
- Instructor has same previlidge as enrolled student, but can't modify the contents. 
- Additional priviledge is it can search student
