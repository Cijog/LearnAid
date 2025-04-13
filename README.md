# **LearnAid – Scholarship Management Portal**

**LearnAid** is a full-stack web application built using **Flask** and **MySQL**, designed to bring transparency, efficiency, and accessibility to the **scholarship ecosystem**. It acts as a bridge between **students** seeking financial support and **organizations** offering scholarships, while giving **administrators** complete control over platform operations, validations, and reporting.

## **User Roles & Workflow**

1. **Applicants (Students)**  
   Students can register by providing their academic and personal information. The registration flow includes:
   - **Uploading a resume** and **income proof** (validated at backend).
   - Logging in using **secure credentials**.
   - Applying to listed scholarships that match their eligibility.
   - Adding a **cover letter** while applying.
   - Tracking the **status of their applications** in real time.
   - Receiving **email notifications** on status updates like *accepted* or *declined*.

2. **Recruiters (Organizations / Companies)**  
   Recruiters must first **submit a registration request**, which is reviewed by the Admin. Upon approval:
   - They can **post scholarships** with specific eligibility criteria, financial details, deadlines, and target audience.
   - View and manage **applicant profiles** and their submitted documents.
   - **Sort applicants** using sentiment-based cover letter analysis (TF-IDF & cosine similarity ready backend).
   - Accept or reject applications with one click, triggering automatic **email notifications**.
   - Post multiple scholarships, each tailored to different applicant categories.

3. **Admin (System Administrator)**  
   The admin oversees and maintains the entire ecosystem:
   - **Approves or rejects recruiter registration requests**.
   - Manages all users — both students and recruiters.
   - Can delete or block users in case of suspicious activity.
   - Handles and responds to **feedback, complaints, and inquiries** sent by users.
   - Generates **insightful reports** on:
     - Number of applications submitted
     - Recruiter activity
     - Scholarship engagement trends
     - Platform usage metrics

## **Communication & Notification System**

- Built-in **email system** alerts users whenever:
  - An application is accepted or rejected
  - A recruiter request is approved/denied
  - Important updates or changes are made to scholarships

- A **messages module** captures user feedback, categorized by **type** (complaint, enquiry, or suggestion), ensuring actionable insights for administrators.

## **Future-Ready Smart Backend**

- The resume analysis feature is backed by **TF-IDF** and **cosine similarity models**, enabling intelligent shortlisting based on content relevance — ideal for recruiter use during high application volumes.
- Modular backend structure allows **easy integration of ML models**, analytics dashboards, and filtering tools.

## **File Management & Validation**

- Users can upload:
  - **Resume (CV)**
  - **Income Proof**
  - **Cover Letter** (for sentiment-based insights)

- Each file undergoes basic format and content validation to ensure data quality.

