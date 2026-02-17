-- Seed data for development (MySQL)

INSERT INTO hospitals (name, address, city, state, zip_code, phone, email) VALUES
('City General Hospital', '123 Main Street', 'New York', 'NY', '10001', '212-555-0100', 'info@citygeneralhospital.com'),
('Memorial Medical Center', '456 Oak Avenue', 'Los Angeles', 'CA', '90001', '213-555-0200', 'contact@memorialmedical.com'),
('Riverside Community Hospital', '789 River Road', 'Chicago', 'IL', '60601', '312-555-0300', 'info@riversidecommunity.com');

INSERT INTO doctors (hospital_id, first_name, last_name, specialization, phone, email, consultation_duration) VALUES
(1, 'John', 'Smith', 'Cardiology', '212-555-1001', 'john.smith@citygeneralhospital.com', 45),
(1, 'Emily', 'Johnson', 'Pediatrics', '212-555-1002', 'emily.johnson@citygeneralhospital.com', 30),
(2, 'Michael', 'Williams', 'Orthopedics', '213-555-2001', 'michael.williams@memorialmedical.com', 40),
(2, 'Sarah', 'Brown', 'Dermatology', '213-555-2002', 'sarah.brown@memorialmedical.com', 30),
(3, 'David', 'Jones', 'Neurology', '312-555-3001', 'david.jones@riversidecommunity.com', 50),
(3, 'Lisa', 'Garcia', 'General Practice', '312-555-3002', 'lisa.garcia@riversidecommunity.com', 25);

INSERT INTO patients (first_name, last_name, date_of_birth, gender, phone, email, address, emergency_contact, emergency_phone, medical_history) VALUES
('Alice', 'Anderson', '1985-03-15', 'Female', '555-1001', 'alice.anderson@email.com', '100 Park Ave, New York, NY 10001', 'Bob Anderson', '555-1002', 'Hypertension'),
('Bob', 'Baker', '1990-07-22', 'Male', '555-1003', 'bob.baker@email.com', '200 Elm St, New York, NY 10002', 'Carol Baker', '555-1004', 'Diabetes Type 2'),
('Carol', 'Clark', '1978-11-30', 'Female', '555-1005', 'carol.clark@email.com', '300 Maple Dr, Los Angeles, CA 90002', 'David Clark', '555-1006', NULL),
('Daniel', 'Davis', '1995-05-18', 'Male', '555-1007', 'daniel.davis@email.com', '400 Pine Ln, Los Angeles, CA 90003', 'Eve Davis', '555-1008', 'Asthma'),
('Eve', 'Evans', '1982-09-25', 'Female', '555-1009', 'eve.evans@email.com', '500 Cedar Rd, Chicago, IL 60602', 'Frank Evans', '555-1010', NULL),
('Frank', 'Fisher', '1970-02-14', 'Male', '555-1011', 'frank.fisher@email.com', '600 Birch Blvd, Chicago, IL 60603', 'Grace Fisher', '555-1012', 'Heart disease'),
('Grace', 'Green', '1988-12-08', 'Female', '555-1013', 'grace.green@email.com', '700 Spruce Way, New York, NY 10003', 'Henry Green', '555-1014', NULL),
('Henry', 'Hill', '1992-04-20', 'Male', '555-1015', 'henry.hill@email.com', '800 Willow Ct, Los Angeles, CA 90004', 'Iris Hill', '555-1016', 'Allergies'),
('Iris', 'Ivy', '1975-08-17', 'Female', '555-1017', 'iris.ivy@email.com', '900 Ash Pl, Chicago, IL 60604', 'Jack Ivy', '555-1018', NULL),
('Jack', 'James', '1998-06-05', 'Male', '555-1019', 'jack.james@email.com', '1000 Oak St, New York, NY 10004', 'Karen James', '555-1020', NULL);

-- doctor_availability and appointments (omitted for brevity in this snippet)
-- Add resources and admin user
INSERT INTO admins (username, email, password_hash, full_name, is_active) VALUES ('admin', 'admin@hospital.com', 'pbkdf2:sha256:changeme', 'System Administrator', 1);