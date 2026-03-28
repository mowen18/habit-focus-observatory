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
    dc.deep_work_minutes,
    COALESCE(c.total_caffeine_mg, 0) AS total_caffeine_mg,
    COALESCE(c.caffeine_after_2pm, 0) AS caffeine_after_2pm,
    COALESCE(e.total_exercise_minutes, 0) AS total_exercise_minutes,
    COALESCE(e.high_intensity_flag, 0) AS high_intensity_flag,
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
