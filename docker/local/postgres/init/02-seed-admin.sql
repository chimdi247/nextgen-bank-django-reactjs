-- =============================================================================
-- Default administrator
--
--   e-mail   : admin@example.com
--   password : password123
--   role     : branch_manager  (+ is_staff / is_superuser: Django admin, every staff screen in the UI)
--
-- The password is stored as a Django PBKDF2-SHA256 hash (600 000 iterations): Django verifies it and transparently
-- upgrades it to Argon2, the project's preferred hasher, at the first successful login.
--
-- LOGIN IS TWO-STEP: after the password an OTP is e-mailed. With docker compose it lands in Mailpit:
--   http://localhost:8025
-- CHANGE THIS PASSWORD before exposing the stack anywhere other than your machine.
-- =============================================================================
INSERT INTO user_auth_user (
    id, password, last_login, is_superuser, is_staff, is_active, date_joined, username,
    security_question, security_answer, email, first_name, middle_name, last_name, id_no,
    account_status, role, failed_login_attempts, last_failed_login, otp, otp_expiry_time)
VALUES (
    'a0000000-0000-4000-8000-000000000001', 'pbkdf2_sha256$600000$k3fkjm3upnuyohwi3i74iq$A4NazgZIoXg7+ZgRNu7f4i9vFRzss5+qCueOmcPolaY=', NULL, TRUE, TRUE, TRUE, now(), 'NB-ADMIN0001',
    'favorite_color', 'blue', 'admin@example.com', 'System', NULL, 'Admin', 10000001,
    'active', 'branch_manager', 0, NULL, '', NULL)
ON CONFLICT (email) DO NOTHING;

-- the application creates a profile through a post_save signal; a raw INSERT bypasses signals, so create it here
INSERT INTO user_profile_profile (
    id, created_at, updated_at, title, gender, date_of_birth, country_of_birth, place_of_birth, marital_status,
    means_of_identification, id_issue_date, id_expiry_date, passport_number, nationality, phone_number, address, city,
    country, employment_status, employer_name, annual_income, user_id)
VALUES (
    'b0000000-0000-4000-8000-000000000001', now(), now(), 'mr', 'male', '1985-01-01', 'KE', 'Nairobi', 'single',
    'national_id', '2020-01-01', '2035-01-01', NULL, 'Kenyan', '+254700000001', '1 Admin Plaza', 'Nairobi',
    'KE', 'employed', 'NextGen Bank', 0, 'a0000000-0000-4000-8000-000000000001')
ON CONFLICT (user_id) DO NOTHING;
