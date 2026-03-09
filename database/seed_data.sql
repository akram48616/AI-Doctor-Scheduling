-- database/seed_data.sql
PRAGMA foreign_keys = ON;

-- Hospitals
INSERT INTO hospitals (name, address, city, state, zip_code, phone, email)
VALUES 
('General Hospital', '123 Main St', 'Metroville', 'State', '00000', '1234567890', 'contact@general.example'),
('Northside Medical Center', '45 North Ave', 'Metroville', 'State', '00001', '1231231234', 'info@northside.example'),
('Eastside Clinic', '200 East Rd', 'Metroville', 'State', '00002', '5556667777', 'hello@eastside.example');

-- Doctors (hospital_id, first_name, last_name, specialization, phone, email, consultation_duration)
INSERT INTO doctors (hospital_id, first_name, last_name, specialization, phone, email, consultation_duration)
VALUES
(1, 'Alice', 'Smith', 'Cardiology', '1112223333', 'alice.smith@general.example', 30),
(1, 'Bob', 'Jones', 'General', '2223334444', 'bob.jones@general.example', 30),
(2, 'Carol', 'Nguyen', 'Pediatrics', '3334445555', 'carol.nguyen@northside.example', 20),
(2, 'David', 'Patel', 'Orthopedics', '4445556666', 'david.patel@northside.example', 40),
(3, 'Eve', 'Khan', 'Dermatology', '5557778888', 'eve.khan@eastside.example', 25);

-- Patients (first_name, last_name, date_of_birth, gender, phone, email)
INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email)
VALUES
('John', 'Doe', '1980-01-01', 'M', '9998887777', 'john.doe@example.com'),
('Maria', 'Garcia', '1992-06-15', 'F', '8887776666', 'maria.garcia@example.com'),
('Liam', 'Chen', '1975-11-30', 'M', '7776665555', 'liam.chen@example.com'),
('Aisha', 'Khan', '2000-03-22', 'F', '6665554444', 'aisha.khan@example.com'),
('Noah', 'Singh', '1988-09-10', 'M', '5554443333', 'noah.singh@example.com');

-- Doctor availability (doctor_id, day_of_week [0=Mon], start_time, end_time, is_available)
-- Alice (Cardiology) available Mon-Fri 09:00-17:00
INSERT INTO doctor_availability (doctor_id, day_of_week, start_time, end_time, is_available)
VALUES
(1, 0, '09:00', '17:00', 1),
(1, 1, '09:00', '17:00', 1),
(1, 2, '09:00', '17:00', 1),
(1, 3, '09:00', '17:00', 1),
(1, 4, '09:00', '17:00', 1),

-- Bob (General) available Mon, Wed, Fri 08:00-12:00
(2, 0, '08:00', '12:00', 1),
(2, 2, '08:00', '12:00', 1),
(2, 4, '08:00', '12:00', 1),

-- Carol (Pediatrics) Tue-Thu 10:00-16:00
(3, 1, '10:00', '16:00', 1),
(3, 2, '10:00', '16:00', 1),
(3, 3, '10:00', '16:00', 1),

-- David (Orthopedics) Mon-Fri 13:00-18:00
(4, 0, '13:00', '18:00', 1),
(4, 1, '13:00', '18:00', 1),
(4, 2, '13:00', '18:00', 1),
(4, 3, '13:00', '18:00', 1),
(4, 4, '13:00', '18:00', 1),

-- Eve (Dermatology) Sat 09:00-13:00, Sun 10:00-14:00
(5, 5, '09:00', '13:00', 1),
(5, 6, '10:00', '14:00', 1);

-- Example appointments (patient_id, doctor_id, hospital_id, appointment_datetime, duration_minutes, status, no_show_probability, reason)
-- Use ISO datetime strings (UTC assumed by app). Adjust dates as needed for tests.
INSERT INTO appointments (patient_id, doctor_id, hospital_id, appointment_datetime, duration_minutes, status, no_show_probability, reason)
VALUES
-- Upcoming appointments
(1, 1, 1, '2026-03-16T09:00:00', 30, 'SCHEDULED', 0.12, 'Routine checkup'),
(2, 1, 1, '2026-03-16T09:30:00', 30, 'CONFIRMED', 0.05, 'Follow-up'),
(3, 2, 1, '2026-03-16T08:00:00', 30, 'SCHEDULED', 0.20, 'General consultation'),
(4, 3, 2, '2026-03-17T10:30:00', 20, 'SCHEDULED', 0.30, 'Child vaccination'),
(5, 4, 2, '2026-03-16T14:00:00', 40, 'CONFIRMED', 0.08, 'Knee pain'),

-- Past appointments (for ML training / history)
(1, 1, 1, '2026-02-10T10:00:00', 30, 'COMPLETED', 0.00, 'Completed visit'),
(2, 2, 1, '2026-02-11T08:30:00', 30, 'NO_SHOW', 0.75, 'No-show recorded'),
(3, 3, 2, '2026-02-12T11:00:00', 20, 'COMPLETED', 0.00, 'Vaccination'),

-- Edge cases: overlapping attempted bookings (to test unique constraint)
(5, 1, 1, '2026-03-16T09:00:00', 30, 'SCHEDULED', 0.15, 'Overbook test');

-- Notes:
-- The last row intentionally duplicates doctor 1 at 2026-03-16T09:00:00 to exercise the unique constraint in tests.