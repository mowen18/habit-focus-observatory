-- Shows average focus by sleep duration bucket.
WITH sleep_bucketed AS (
    SELECT
        CASE
            WHEN sleep_hours < 6 THEN '<6'
            WHEN sleep_hours < 7 THEN '6-7'
            WHEN sleep_hours < 8 THEN '7-8'
            ELSE '8+'
        END AS sleep_bucket,
        CASE
            WHEN sleep_hours < 6 THEN 1
            WHEN sleep_hours < 7 THEN 2
            WHEN sleep_hours < 8 THEN 3
            ELSE 4
        END AS bucket_order,
        focus_rating
    FROM daily_metrics_vw
    WHERE sleep_hours IS NOT NULL
      AND focus_rating IS NOT NULL
)
SELECT
    sleep_bucket,
    COUNT(*) AS day_count,
    ROUND(AVG(focus_rating)::NUMERIC, 2) AS avg_focus_rating
FROM sleep_bucketed
GROUP BY sleep_bucket, bucket_order
ORDER BY bucket_order;

-- Compares average energy on days with and without afternoon caffeine.
SELECT
    caffeine_after_2pm,
    COUNT(*) AS day_count,
    ROUND(AVG(energy_rating)::NUMERIC, 2) AS avg_energy_rating
FROM daily_metrics_vw
WHERE energy_rating IS NOT NULL
GROUP BY caffeine_after_2pm
ORDER BY caffeine_after_2pm;

-- Shows next-day focus following days that did or did not include high-intensity exercise.
WITH next_day_focus AS (
    SELECT
        behavior_day.checkin_date,
        behavior_day.high_intensity_flag,
        behavior_day.focus_rating,
        next_day.focus_rating AS next_day_focus_rating
    FROM daily_metrics_vw AS behavior_day
    LEFT JOIN daily_metrics_vw AS next_day
        ON next_day.checkin_date = behavior_day.checkin_date + 1
    WHERE behavior_day.high_intensity_flag IS NOT NULL
)
SELECT
    high_intensity_flag,
    COUNT(*) AS day_count,
    ROUND(AVG(next_day_focus_rating)::NUMERIC, 2) AS avg_next_day_focus_rating
FROM next_day_focus
WHERE next_day_focus_rating IS NOT NULL
GROUP BY high_intensity_flag
ORDER BY high_intensity_flag;

-- Compares exercise volume on high-focus days versus other days.
SELECT
    CASE
        WHEN focus_rating >= 8 THEN 'high_focus_day'
        ELSE 'other_day'
    END AS high_focus_day_bucket,
    COUNT(*) AS day_count,
    ROUND(AVG(total_exercise_minutes)::NUMERIC, 2) AS avg_daily_exercise_minutes
FROM daily_metrics_vw
WHERE focus_rating IS NOT NULL
GROUP BY 1
ORDER BY high_focus_day_bucket;

-- Lists daily metrics in date order for quick manual inspection.
SELECT
    checkin_date,
    sleep_hours,
    sleep_quality,
    energy_rating,
    focus_rating,
    mood_rating,
    stress_rating,
    deep_work_minutes,
    total_caffeine_mg,
    caffeine_after_2pm,
    total_exercise_minutes,
    high_intensity_flag,
    prior_day_sleep_hours,
    focus_7d_avg
FROM daily_metrics_vw
ORDER BY checkin_date;
