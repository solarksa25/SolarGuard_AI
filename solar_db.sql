-- phpMyAdmin SQL Dump
-- version 5.1.2
-- https://www.phpmyadmin.net/
--
-- Host: localhost:8889
-- Generation Time: May 20, 2026 at 09:28 PM
-- Server version: 5.7.24
-- PHP Version: 8.3.1

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `solar_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `alerts`
--

CREATE TABLE `alerts` (
  `id` int(11) NOT NULL,
  `severity` enum('normal','warning','critical') DEFAULT 'warning',
  `alert_type` varchar(100) DEFAULT '',
  `source_key` varchar(100) DEFAULT '',
  `description` text,
  `recommendation` text,
  `status` enum('active','investigating','resolved','snoozed') DEFAULT 'active',
  `detected_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `resolved_by` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `alerts`
--

INSERT INTO `alerts` (`id`, `severity`, `alert_type`, `source_key`, `description`, `recommendation`, `status`, `detected_at`, `updated_at`, `resolved_by`) VALUES
(250, 'warning', 'Partial Shading', 'INV-01', '[Live AI Monitor] INV-01: Partial Shading detected with 100.0% confidence. Model: LGB', 'Partial shading detected. Inspect for obstructions and check bypass diodes.', 'active', '2026-05-20 13:40:15', '2026-05-20 13:40:15', NULL),
(251, 'warning', 'Partial Shading', 'INV-01', '[Live AI Monitor] INV-01: Partial Shading detected with 100.0% confidence. Model: LGB', 'Partial shading detected. Inspect for obstructions and check bypass diodes.', 'active', '2026-05-20 13:41:33', '2026-05-20 13:41:32', NULL),
(252, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 46.3% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:42:54', '2026-05-20 13:42:53', NULL),
(253, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 72.6% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:42:55', '2026-05-20 13:42:54', NULL),
(254, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 52.4% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:42:56', '2026-05-20 13:42:56', NULL),
(255, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 43.1% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:42:59', '2026-05-20 13:42:59', NULL),
(256, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 73.0% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:01', '2026-05-20 13:43:00', NULL),
(257, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 49.5% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:43:03', '2026-05-20 13:43:02', NULL),
(258, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 78.2% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:43:05', '2026-05-20 13:43:05', NULL),
(259, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 52.7% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:11', '2026-05-20 13:43:11', NULL),
(260, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 50.5% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:20', '2026-05-20 13:43:19', NULL),
(261, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 62.2% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:23', '2026-05-20 13:43:23', NULL),
(262, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 70.9% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:43:28', '2026-05-20 13:43:27', NULL),
(263, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 63.4% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:29', '2026-05-20 13:43:29', NULL),
(264, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 56.8% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:43:32', '2026-05-20 13:43:31', NULL),
(265, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 79.9% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:33', '2026-05-20 13:43:32', NULL),
(266, 'critical', 'Open-Circuit String', 'INV-01', '[Live AI Monitor] INV-01: Open-Circuit String detected with 51.2% confidence. Model: LGB', 'Open-circuit string detected. Check fuses and MC4 connectors.', 'active', '2026-05-20 13:43:53', '2026-05-20 13:43:52', NULL),
(267, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 61.5% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:56', '2026-05-20 13:43:56', NULL),
(268, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 46.1% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:43:59', '2026-05-20 13:43:58', NULL),
(269, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 49.5% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:44:01', '2026-05-20 13:44:00', NULL),
(270, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 74.8% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:44:02', '2026-05-20 13:44:02', NULL),
(271, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 78.8% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'active', '2026-05-20 13:44:05', '2026-05-20 13:44:04', NULL),
(272, 'warning', 'Sensor Fault', 'INV-01', '[Live AI Monitor] INV-01: Sensor Fault detected with 63.5% confidence. Model: LGB', 'Sensor fault detected. Verify sensor wiring and calibration.', 'active', '2026-05-20 13:44:08', '2026-05-20 13:44:08', NULL),
(273, 'warning', 'Degradation', 'INV-01', '[Live AI Monitor] INV-01: Degradation detected with 79.2% confidence. Model: LGB', 'Degradation detected. Compare against baseline and consider IV curve tracing.', 'active', '2026-05-20 13:44:09', '2026-05-20 13:44:09', NULL),
(274, 'warning', 'Soiling', 'INV-01', '[Live AI Monitor] INV-01: Soiling detected with 73.9% confidence. Model: LGB', 'Dust/soiling detected. Schedule panel cleaning within 24-48 hours.', 'resolved', '2026-05-20 13:44:11', '2026-05-20 22:28:20', 2);

-- --------------------------------------------------------

--
-- Table structure for table `analysis_results`
--

CREATE TABLE `analysis_results` (
  `id` int(11) NOT NULL,
  `user_id` int(11) DEFAULT NULL,
  `filename` varchar(255) DEFAULT '',
  `row_count` int(11) DEFAULT '0',
  `inverter_count` int(11) DEFAULT '0',
  `anomaly_count` int(11) DEFAULT '0',
  `fault_type` varchar(100) DEFAULT '',
  `health_score` float DEFAULT '100',
  `analysis_date` datetime DEFAULT CURRENT_TIMESTAMP,
  `model_used` varchar(50) DEFAULT '',
  `stored_filename` varchar(255) DEFAULT ''
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `analysis_results`
--

INSERT INTO `analysis_results` (`id`, `user_id`, `filename`, `row_count`, `inverter_count`, `anomaly_count`, `fault_type`, `health_score`, `analysis_date`, `model_used`, `stored_filename`) VALUES
(9, 1, 'generated_dataset_500rows (1).csv', 500, 1, 381, 'Sensor Fault', 23.8, '2026-05-20 11:38:08', 'LightGBM', '90670df965904fd0bff14b5e4c09ce09_generated_dataset_500rows_1.csv'),
(10, 1, 'generated_dataset_500rows (2).csv', 500, 1, 376, 'Sensor Fault', 24.8, '2026-05-20 11:42:23', 'LightGBM', 'fb6da2f14124467da5ee009ce31eb5bd_generated_dataset_500rows_2.csv'),
(11, 1, 'generated_dataset_500rows (3).csv', 500, 2, 258, 'Normal', 48.4, '2026-05-20 13:10:20', 'LightGBM', 'c42acd277c6841bb9898a1c1de1bf477_generated_dataset_500rows_3.csv'),
(12, 1, 'generated_dataset_500rows (4).csv', 500, 2, 370, 'Partial Shading', 26, '2026-05-20 13:10:56', 'LightGBM', 'fcc454ffb52b4c8eac175b0f44b38a7d_generated_dataset_500rows_4.csv'),
(13, 1, 'generated_dataset_500rows (4).csv', 500, 2, 370, 'Partial Shading', 26, '2026-05-20 13:11:24', 'LightGBM', 'fcc454ffb52b4c8eac175b0f44b38a7d_generated_dataset_500rows_4.csv'),
(14, 1, 'processed_dataset_universal.csv', 80941, 2, 23894, 'Normal', 70.5, '2026-05-20 13:15:53', 'LightGBM', '9447f5fd07e14d4a816f98867dcafe36_processed_dataset_universal.csv'),
(15, 1, 'processed_dataset.csv', 80941, 2, 23894, 'Normal', 70.5, '2026-05-20 13:25:34', 'LightGBM', '0a39c5e52fa1456abad214155084d3ae_processed_dataset.csv'),
(16, 1, 'generated_dataset_500rows (5).csv', 500, 2, 500, 'Partial Shading', 0, '2026-05-20 13:38:32', 'LightGBM', 'e2c2178508ea453fa8020781c907b7a3_generated_dataset_500rows_5.csv');

-- --------------------------------------------------------

--
-- Table structure for table `station_settings`
--

CREATE TABLE `station_settings` (
  `id` int(11) NOT NULL DEFAULT '1',
  `station_id` varchar(50) NOT NULL,
  `station_name` varchar(150) NOT NULL,
  `dc_capacity_kw` float NOT NULL,
  `num_inverters` int(11) NOT NULL,
  `inverter_eff` float NOT NULL,
  `pdc0_w` float NOT NULL,
  `gamma_pdc` float NOT NULL,
  `eta_inv` float NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `station_settings`
--

INSERT INTO `station_settings` (`id`, `station_id`, `station_name`, `dc_capacity_kw`, `num_inverters`, `inverter_eff`, `pdc0_w`, `gamma_pdc`, `eta_inv`) VALUES
(1, '2107', 'Arbuckle CA', 893, 24, 0.96, 893000, -0.004, 0.96);

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int(11) NOT NULL,
  `full_name` varchar(150) NOT NULL,
  `phone` varchar(30) DEFAULT '',
  `email` varchar(150) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` enum('admin','engineer') DEFAULT 'engineer',
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Dumping data for table `users`
--

INSERT INTO `users` (`id`, `full_name`, `phone`, `email`, `password_hash`, `role`, `created_at`) VALUES
(1, 'Admin', '', 'admin@gmail.com', '$2b$12$/b.lNd3SKKjBptaXUeL6uOJns006Gq1H8CMJ3P5vds1djli2Jcz5q', 'admin', '2026-05-19 12:48:49'),
(2, 'Bassam', '0545634234', 'bassam@gmail.com', '$2b$12$6CTVLsEsQnDSkbaDTFBl/e89e3qJv6kaqHKvKuyfDeFA7u56GIkSu', 'engineer', '2026-05-20 19:26:19');

--
-- Indexes for dumped tables
--

--
-- Indexes for table `alerts`
--
ALTER TABLE `alerts`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_status` (`status`),
  ADD KEY `idx_severity` (`severity`),
  ADD KEY `idx_detected` (`detected_at`);

--
-- Indexes for table `analysis_results`
--
ALTER TABLE `analysis_results`
  ADD PRIMARY KEY (`id`),
  ADD KEY `idx_date` (`analysis_date`);

--
-- Indexes for table `station_settings`
--
ALTER TABLE `station_settings`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `email` (`email`),
  ADD KEY `idx_email` (`email`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `alerts`
--
ALTER TABLE `alerts`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=275;

--
-- AUTO_INCREMENT for table `analysis_results`
--
ALTER TABLE `analysis_results`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=17;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=3;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
