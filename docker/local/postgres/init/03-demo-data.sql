-- =============================================================================
-- OPTIONAL demo data: two verified customers with funded accounts and a little history, so the UI is not empty.
-- Delete this file (before the first start) if you do not want it.
--
--   alice@example.com / password123   USD current account 1000110000000015
--   bob@example.com   / password123   USD current account 1000110000000024
-- =============================================================================
INSERT INTO user_auth_user (
    id, password, is_superuser, is_staff, is_active, date_joined, username,
    security_question, security_answer, email, first_name, middle_name, last_name, id_no,
    account_status, role, failed_login_attempts, otp)
VALUES
 ('a0000000-0000-4000-8000-000000000002', 'pbkdf2_sha256$600000$46qerte5psmj3j7w7cjj55$qziTFI3lKhRheRAoGKAmuqllNmqnjV3oCq4bvakChvY=', FALSE, FALSE, TRUE, now(), 'NB-ALICE0002',
  'favorite_color', 'blue', 'alice@example.com', 'Alice', NULL, 'Johnson', 10000002, 'active', 'customer', 0, ''),
 ('a0000000-0000-4000-8000-000000000003', 'pbkdf2_sha256$600000$46qerte5psmj3j7w7cjj55$qziTFI3lKhRheRAoGKAmuqllNmqnjV3oCq4bvakChvY=', FALSE, FALSE, TRUE, now(), 'NB-BOB000003',
  'favorite_color', 'blue', 'bob@example.com', 'Bob', NULL, 'Mwangi', 10000003, 'active', 'customer', 0, '')
ON CONFLICT (email) DO NOTHING;

INSERT INTO user_profile_profile (
    id, created_at, updated_at, title, gender, date_of_birth, country_of_birth, place_of_birth, marital_status,
    means_of_identification, id_issue_date, id_expiry_date, nationality, phone_number, address, city, country,
    employment_status, employer_name, annual_income, user_id, account_currency, account_type)
VALUES
 ('b0000000-0000-4000-8000-000000000002', now(), now(), 'mrs', 'female', '1992-04-12', 'KE', 'Nairobi', 'single',
  'national_id', '2021-01-01', '2036-01-01', 'Kenyan', '+254711000002', '12 Riverside Drive', 'Nairobi', 'KE',
  'employed', 'Acme Ltd', 60000, 'a0000000-0000-4000-8000-000000000002', 'us_dollar', 'current'),
 ('b0000000-0000-4000-8000-000000000003', now(), now(), 'mr', 'male', '1988-09-30', 'KE', 'Mombasa', 'married',
  'drivers_license', '2021-01-01', '2036-01-01', 'Kenyan', '+254722000003', '5 Harbour Road', 'Mombasa', 'KE',
  'self_employed', NULL, 45000, 'a0000000-0000-4000-8000-000000000003', 'us_dollar', 'current')
ON CONFLICT (user_id) DO NOTHING;

INSERT INTO accounts_bankaccount (
    id, created_at, updated_at, account_number, account_balance, currency, account_status, account_type, is_primary,
    kyc_submitted, kyc_verified, verification_date, verification_notes, fully_activated, user_id, verified_by_id, interest_rate)
VALUES
 ('c0000000-0000-4000-8000-000000000002', now() - interval '30 days', now(), '1000110000000015', 24750.00, 'us_dollar', 'active', 'current', TRUE,
  TRUE, TRUE, now() - interval '29 days', 'Seeded demo account', TRUE, 'a0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000001', 0.0000),
 ('c0000000-0000-4000-8000-000000000003', now() - interval '30 days', now(), '1000110000000024', 5250.00, 'us_dollar', 'active', 'current', TRUE,
  TRUE, TRUE, now() - interval '29 days', 'Seeded demo account', TRUE, 'a0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000001', 0.0000)
ON CONFLICT (account_number) DO NOTHING;

-- history: two cash deposits made by the admin acting as teller, and one transfer Alice -> Bob
INSERT INTO accounts_transaction (
    id, created_at, updated_at, amount, description, status, transaction_type,
    receiver_id, receiver_account_id, sender_id, sender_account_id, user_id)
VALUES
 ('d0000000-0000-4000-8000-000000000001', now() - interval '20 days', now() - interval '20 days', 25000.00, 'Cash deposit at branch by System Admin', 'completed', 'deposit',
  'a0000000-0000-4000-8000-000000000002', 'c0000000-0000-4000-8000-000000000002', NULL, NULL, 'a0000000-0000-4000-8000-000000000001'),
 ('d0000000-0000-4000-8000-000000000002', now() - interval '19 days', now() - interval '19 days', 5000.00, 'Cash deposit at branch by System Admin', 'completed', 'deposit',
  'a0000000-0000-4000-8000-000000000003', 'c0000000-0000-4000-8000-000000000003', NULL, NULL, 'a0000000-0000-4000-8000-000000000001'),
 ('d0000000-0000-4000-8000-000000000003', now() - interval '2 days', now() - interval '2 days', 250.00, 'Rent share', 'completed', 'transfer',
  'a0000000-0000-4000-8000-000000000003', 'c0000000-0000-4000-8000-000000000003', 'a0000000-0000-4000-8000-000000000002', 'c0000000-0000-4000-8000-000000000002', 'a0000000-0000-4000-8000-000000000002')
ON CONFLICT (id) DO NOTHING;
