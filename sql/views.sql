-- Provides one daily analytics row by combining check-ins with caffeine and exercise summaries.
CREATE OR REPLACE VIEW daily_metrics_vw AS
WITH daily_caffeine AS (
    SELECT
        checkin_date,
        SUM(caffeine_mg) AS total_caffeine_mg,
        MAX(CASE WHEN intake_time >= TIME '14:00' THEN 1 ELSE 0 END) AS caffeine_after_2pm
    FROM caffeine_log
    GROUP BY checkin_date
),
daily_exercise AS (
    SELECT
        checkin_date,
        SUM(duration_minutes) AS total_exercise_minutes,
        MAX(CASE WHEN intensity = 'high' THEN 1 ELSE 0 END) AS high_intensity_flag
    FROM exercise_log
    GROUP BY checkin_date
)
SELECT
    dc.checkin_date,
    dc.sleep_hours,
    dc.sleep_quality,
    dc.energy_rating,
    dc.focus_rating,
    dc.mood_rating,
    dc.stress_rating,
    CASE
        WHEN dc.deep_work_logged THEN COALESCE(dc.deep_work_minutes, 0)
        ELSE NULL
    END AS deep_work_minutes,
    CASE
        WHEN dc.caffeine_logged THEN COALESCE(c.total_caffeine_mg, 0)
        ELSE NULL
    END AS total_caffeine_mg,
    CASE
        WHEN dc.caffeine_logged THEN COALESCE(c.caffeine_after_2pm, 0)
        ELSE NULL
    END AS caffeine_after_2pm,
    CASE
        WHEN dc.exercise_logged THEN COALESCE(e.total_exercise_minutes, 0)
        ELSE NULL
    END AS total_exercise_minutes,
    CASE
        WHEN dc.exercise_logged THEN COALESCE(e.high_intensity_flag, 0)
        ELSE NULL
    END AS high_intensity_flag,
    LAG(dc.sleep_hours) OVER (ORDER BY dc.checkin_date) AS prior_day_sleep_hours,
    AVG(dc.focus_rating) OVER (
        ORDER BY dc.checkin_date
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS focus_7d_avg
FROM daily_checkin AS dc
LEFT JOIN daily_caffeine AS c
    ON dc.checkin_date = c.checkin_date
LEFT JOIN daily_exercise AS e
    ON dc.checkin_date = e.checkin_date;

-- Provides one daily completeness row showing which workflow sections were logged.
CREATE OR REPLACE VIEW daily_completeness_vw AS
WITH section_status AS (
    SELECT
        dc.checkin_date,
        (
            dc.sleep_hours IS NOT NULL
            OR dc.sleep_quality IS NOT NULL
            OR dc.energy_rating IS NOT NULL
            OR dc.focus_rating IS NOT NULL
            OR dc.mood_rating IS NOT NULL
            OR dc.stress_rating IS NOT NULL
            OR dc.notes IS NOT NULL
        ) AS has_checkin,
        dc.deep_work_logged AS has_deep_work_entry,
        dc.caffeine_logged AS has_caffeine_entry,
        dc.exercise_logged AS has_exercise_entry
    FROM daily_checkin AS dc
)
SELECT
    checkin_date,
    has_checkin,
    has_deep_work_entry,
    has_caffeine_entry,
    has_exercise_entry,
    (
        has_checkin::INTEGER
        + has_deep_work_entry::INTEGER
        + has_caffeine_entry::INTEGER
        + has_exercise_entry::INTEGER
    ) AS completed_sections,
    4 AS expected_sections,
    ROUND(
        100.0 * (
            has_checkin::INTEGER
            + has_deep_work_entry::INTEGER
            + has_caffeine_entry::INTEGER
            + has_exercise_entry::INTEGER
        ) / 4,
        1
    ) AS completeness_pct
FROM section_status;
