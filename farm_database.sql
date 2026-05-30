-- ============================================================
--  FARM EXPENSE AND HARVEST PROFIT ANALYZER
--  Database Schema — Baras, Rizal
--  CC 103 — Problem Set #3
-- ============================================================
--  HOW TO USE:
--    1. Open MySQL Workbench or CMD
--    2. Run: mysql -u root -p
--    3. Then: source farm_database.sql
--       OR copy-paste this entire file into MySQL Workbench
-- ============================================================

-- Step 1: Create and select the database
CREATE DATABASE IF NOT EXISTS farm_analyzer_db;
USE farm_analyzer_db;

-- ============================================================
--  TABLE 1: crops
--  Stores the list of supported crops
-- ============================================================
CREATE TABLE IF NOT EXISTS crops (
    crop_id     INT AUTO_INCREMENT PRIMARY KEY,
    crop_name   VARCHAR(50)  NOT NULL UNIQUE,
    season_info VARCHAR(100),
    price_guide VARCHAR(150)
);

-- Seed crop data
INSERT INTO crops (crop_name, season_info, price_guide) VALUES
('palay',   'Aug-Dec (1st crop), May-Jul (2nd crop)', 'Raw ₱12-14/kg | Processed ₱24/kg | Milled ₱32.50/kg'),
('mais',    'January - March',                         'Fresh ₱20-30/kg | Dried ₱18-22/kg'),
('okra',    'March - November (warm months)',          'Grade A ₱40-60/kg | Grade B ₱25-35/kg'),
('kamatis', 'October - February (cool season)',        'Premium ₱50-80/kg | Regular ₱30-45/kg'),
('sibuyas', 'October - February (cool season)',        'Red ₱80-120/kg | White ₱60-90/kg'),
('talong',  'Year-round',                              'Long purple ₱35-50/kg | Round ₱40-55/kg')
ON DUPLICATE KEY UPDATE season_info = VALUES(season_info), price_guide = VALUES(price_guide);


-- ============================================================
--  TABLE 2: expense_types
--  Stores the list of expense categories
-- ============================================================
CREATE TABLE IF NOT EXISTS expense_types (
    type_id     INT AUTO_INCREMENT PRIMARY KEY,
    type_name   VARCHAR(80) NOT NULL UNIQUE
);

INSERT INTO expense_types (type_name) VALUES
('binhi / seeds'),
('pataba / fertilizer'),
('pesticide / herbicide'),
('gasolina / fuel'),
('paupahan / labor'),
('irigasyon / irrigation'),
('kagamitan / tools & equipment'),
('lulan / transport to market'),
('pagkain ng hayop / animal feed'),
('iba pa / other')
ON DUPLICATE KEY UPDATE type_name = VALUES(type_name);


-- ============================================================
--  TABLE 3: crop_cycles
--  One record = one planting season for one crop
-- ============================================================
CREATE TABLE IF NOT EXISTS crop_cycles (
    cycle_id    INT AUTO_INCREMENT PRIMARY KEY,
    crop_id     INT          NOT NULL,
    season      VARCHAR(50)  NOT NULL,
    start_date  DATE         NOT NULL,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (crop_id) REFERENCES crops(crop_id)
);


-- ============================================================
--  TABLE 4: expenses
--  All expenses linked to a crop cycle
-- ============================================================
CREATE TABLE IF NOT EXISTS expenses (
    expense_id  INT AUTO_INCREMENT PRIMARY KEY,
    cycle_id    INT            NOT NULL,
    type_id     INT            NOT NULL,
    amount      DECIMAL(10,2)  NOT NULL,
    expense_date DATE          NOT NULL,
    note        VARCHAR(200),
    is_logistics TINYINT(1)    DEFAULT 0,   -- 1 = transport/logistics
    created_at  TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cycle_id) REFERENCES crop_cycles(cycle_id) ON DELETE CASCADE,
    FOREIGN KEY (type_id)  REFERENCES expense_types(type_id)
);


-- ============================================================
--  TABLE 5: harvests
--  Harvest details per crop cycle (one harvest per cycle)
-- ============================================================
CREATE TABLE IF NOT EXISTS harvests (
    harvest_id       INT AUTO_INCREMENT PRIMARY KEY,
    cycle_id         INT            NOT NULL UNIQUE,
    yield_kg         DECIMAL(10,2)  NOT NULL,
    price_per_kg     DECIMAL(10,2)  NOT NULL,
    revenue          DECIMAL(12,2)  GENERATED ALWAYS AS (yield_kg * price_per_kg) STORED,
    harvest_date     DATE           NOT NULL,
    processing_level VARCHAR(60),   -- for palay: raw / processed / milled
    created_at       TIMESTAMP      DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (cycle_id) REFERENCES crop_cycles(cycle_id) ON DELETE CASCADE
);


-- ============================================================
--  USEFUL VIEWS
-- ============================================================

-- View 1: Full summary per crop cycle
CREATE OR REPLACE VIEW view_cycle_summary AS
SELECT
    cc.cycle_id,
    c.crop_name,
    cc.season,
    cc.start_date,
    COALESCE(SUM(e.amount), 0)              AS total_expenses,
    COALESCE(SUM(CASE WHEN e.is_logistics = 1 THEN e.amount ELSE 0 END), 0) AS logistics_cost,
    h.yield_kg,
    h.price_per_kg,
    h.revenue,
    h.processing_level,
    h.harvest_date,
    COALESCE(h.revenue, 0) - COALESCE(SUM(e.amount), 0)  AS net_profit_loss,
    CASE
        WHEN h.revenue IS NULL THEN 'No harvest yet'
        WHEN (h.revenue - COALESCE(SUM(e.amount), 0)) >= 0 THEN 'TUBO / PROFIT'
        ELSE 'LUGI / LOSS'
    END AS status
FROM crop_cycles cc
JOIN crops c ON cc.crop_id = c.crop_id
LEFT JOIN expenses e ON cc.cycle_id = e.cycle_id
LEFT JOIN harvests h ON cc.cycle_id = h.cycle_id
GROUP BY
    cc.cycle_id, c.crop_name, cc.season, cc.start_date,
    h.yield_kg, h.price_per_kg, h.revenue,
    h.processing_level, h.harvest_date;


-- View 2: Expense breakdown per cycle (for distribution chart)
CREATE OR REPLACE VIEW view_expense_breakdown AS
SELECT
    cc.cycle_id,
    c.crop_name,
    cc.season,
    et.type_name,
    SUM(e.amount)                         AS type_total,
    SUM(SUM(e.amount)) OVER (PARTITION BY cc.cycle_id) AS cycle_total,
    ROUND(SUM(e.amount) /
          SUM(SUM(e.amount)) OVER (PARTITION BY cc.cycle_id) * 100, 1) AS percentage
FROM expenses e
JOIN crop_cycles cc  ON e.cycle_id = cc.cycle_id
JOIN crops c         ON cc.crop_id = c.crop_id
JOIN expense_types et ON e.type_id  = et.type_id
GROUP BY cc.cycle_id, c.crop_name, cc.season, et.type_name;


-- View 3: Overall income vs expense analysis
CREATE OR REPLACE VIEW view_income_vs_expense AS
SELECT
    c.crop_name,
    cc.season,
    COALESCE(SUM(e.amount), 0)            AS total_expenses,
    COALESCE(h.revenue, 0)                AS total_revenue,
    COALESCE(h.revenue, 0) - COALESCE(SUM(e.amount), 0) AS net,
    CASE
        WHEN SUM(e.amount) > 0
        THEN ROUND((COALESCE(h.revenue,0) - SUM(e.amount)) / SUM(e.amount) * 100, 1)
        ELSE NULL
    END AS roi_percent
FROM crop_cycles cc
JOIN crops c         ON cc.crop_id = c.crop_id
LEFT JOIN expenses e ON cc.cycle_id = e.cycle_id
LEFT JOIN harvests h ON cc.cycle_id = h.cycle_id
GROUP BY cc.cycle_id, c.crop_name, cc.season, h.revenue;


-- ============================================================
--  SAMPLE DATA (for testing)
-- ============================================================

-- Sample crop cycle: Palay, Wet Season 2025
INSERT INTO crop_cycles (crop_id, season, start_date)
VALUES (1, 'Wet 2025', '2025-08-01');

-- Expenses for cycle 1
INSERT INTO expenses (cycle_id, type_id, amount, expense_date, note) VALUES
(1, 1,  850.00, '2025-08-01', 'IR64 seeds'),
(1, 2, 1200.00, '2025-08-10', 'Complete fertilizer'),
(1, 3,  450.00, '2025-09-05', 'Herbicide'),
(1, 4,  600.00, '2025-09-15', 'Fuel for tractor'),
(1, 5, 2000.00, '2025-10-01', 'Harvest labor'),
(1, 8,  350.00, '2025-12-01', 'Tricycle to market', 1);

-- Harvest for cycle 1 (processed palay @ P24/kg)
INSERT INTO harvests (cycle_id, yield_kg, price_per_kg, harvest_date, processing_level)
VALUES (1, 320.00, 24.00, '2025-12-01', 'Naproseso (processed)');

-- Sample crop cycle: Sibuyas, Cool Season 2025
INSERT INTO crop_cycles (crop_id, season, start_date)
VALUES (5, 'Cool 2025', '2025-10-15');

INSERT INTO expenses (cycle_id, type_id, amount, expense_date, note) VALUES
(2, 1,  500.00, '2025-10-15', 'Onion seedlings'),
(2, 2,  900.00, '2025-10-20', 'Fertilizer'),
(2, 5, 1500.00, '2025-11-10', 'Weeding labor'),
(2, 8,  200.00, '2026-02-01', 'Transport to Antipolo market', 1);

INSERT INTO harvests (cycle_id, yield_kg, price_per_kg, harvest_date, processing_level)
VALUES (2, 180.00, 55.00, '2026-02-01', NULL);


-- ============================================================
--  QUICK REPORT QUERIES (run these to test)
-- ============================================================

-- See all cycle summaries:
-- SELECT * FROM view_cycle_summary;

-- See expense breakdown:
-- SELECT * FROM view_expense_breakdown;

-- See income vs expense analysis:
-- SELECT * FROM view_income_vs_expense;

-- Full expense list for cycle 1:
-- SELECT e.expense_date, et.type_name, e.amount, e.note
-- FROM expenses e
-- JOIN expense_types et ON e.type_id = et.type_id
-- WHERE e.cycle_id = 1;

SELECT 'Database setup complete!' AS message;
