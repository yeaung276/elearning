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
