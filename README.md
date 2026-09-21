# Tuition Center — Frappe Framework v15+ App

A complete, advanced **Tuition / Coaching Centre Management System** built for the **Frappe Framework v15+** (works standalone on plain Frappe; ERPNext not required).

> App name (Python module): `tution_center` · DocType prefix: `TC`

---

## ✨ Features

### Academics
- **Course** catalogue with levels, fees and per-course student counters
- **Batch / Class Group** with schedule, room, teacher, seat capacity & live fill-rate
- **Academic Term** (terms/semesters) and **Assessment Structure** per course
- **Room / Location** registry to avoid double booking

### People
- **Student** profiles with photo, guardians, custom user portal accounts
- **Guardian** linked to students with relationship & contact info
- **Teacher / Instructor** profiles linked to Frappe users & employees

### Fees & Payments
- **Fee Structure** builder (components + discounts + taxes) with ** Fee Schedule** bulk generation per batch/term
- **Fee Enrolment** ledger per student (auto-created from Fee Schedule, tracks paid/outstanding)
- **Payments** with **part-payment support**, payment modes, reference numbers, auto student-status sync
- **Invoice Print Format** & receipt PDF ready

### Attendance
- **Student Group → Attendance Tool**: mark daily attendance for a batch in one screen
- Monthly attendance percentage roll-up used in eligibility rules

### Exams & Results
- **Exam** scheduling per batch/subject with invigilator and room
- **Exam Result** entry with auto pass/fail, per-exam student counters
- **Assessment Criteria** / grading scales

### Learning
- **Announcements** (students/teachers, expiring, pinned, email broadcast)
- **Assignments** with due dates, status tracking and results
- **Timetable** per batch with clash detection, plus a read-only **Timetable Portal** page for students/teachers
- **Library** (books & issues), **Certificates** (auto-numbered), **Complaints** (with auto escalation)

### Messaging & Automation
- **SMS / Notification Reminder** console (frappe.sms support) + scheduled **Fee Reminders** every morning
- **WhatsApp-ready** link generation per student
- Daily digest via hooks

### Portal & UX
- Student/Guardian **Web Portal**: my courses, fees, invoices, results, timetable, announcements
- **Frappe v15 native** — modern JSON DocTypes, workspace, dashboards, number cards, charts
- Roles: `Tuition Manager`, `Tuition Teacher`, `Student`, `Guardian`
- Full REST API via Frappe + dedicated whitelisted endpoints

---

## Installation (bench)

```bash
cd $PATH_TO_BENCH
bench get-app https://github.com/joshent31/tution-Center.git
bench --site yoursite.local install-app tution_center
bench --site yoursite.local migrate
bench build --app tution_center
bench restart
```

> ⚠️ App name is `tution_center` (Python module name), repo name is `tution-Center`.

## Roles & Permissions

| Role | Access |
|------|--------|
| Tuition Manager | Full CRUD on all doctypes |
| Tuition Teacher | Read/create attendance, exams, assignments, announcements, results |
| Student | Portal access to own fees, results, timetable, announcements |
| Guardian | Portal access to linked children's data |

## Key Doctypes

Course, Batch, Academic Term, Room, Teacher, Student, Guardian,
Fee Structure, Fee Schedule, Fee Enrolment, Payment, Assessment Structure,
Assessment Criterion, Exam, Exam Result, Attendance Tool, Student Attendance,
Announcement, Assignment, Timetable, Book, Book Issue, Certificate, Complaint,
Notification Reminder

## License

MIT
