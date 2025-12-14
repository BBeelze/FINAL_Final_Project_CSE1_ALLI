CREATE DATABASE motorcycles_db;
USE motorcycles_db;

CREATE TABLE motorcycles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    make VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    year INT NOT NULL,
    engine_cc INT NOT NULL,
    color VARCHAR(50) NOT NULL
);

-- Insert 21+ realistic motorcycle records
INSERT INTO motorcycles (make, model, year, engine_cc, color) VALUES
('Yamaha', 'YZF-R1', 2022, 998, 'Team Blue'),
('Honda', 'CBR600RR', 2021, 599, 'Tricolor'),
('Kawasaki', 'Ninja ZX-10R', 2023, 998, 'Lime Green'),
('Suzuki', 'GSX-R750', 2020, 749, 'Metallic Matte Black'),
('Ducati', 'Panigale V4', 2023, 1103, 'Ducati Red'),
('BMW', 'S 1000 RR', 2022, 999, 'Racing Blue'),
('Aprilia', 'RSV4', 2021, 1099, 'Aprilia Red'),
('Harley-Davidson', 'Sportster S', 2022, 1252, 'Vivid Black'),
('Triumph', 'Street Triple RS', 2023, 765, 'Matt Silver Ice'),
('KTM', '1290 Super Duke R', 2022, 1301, 'Orange'),
('MV Agusta', 'F4', 2020, 998, 'Rosso Corsa'),
('Yamaha', 'MT-09', 2023, 889, 'Icon Blue'),
('Honda', 'Africa Twin', 2022, 1084, 'Grand Prix Red'),
('Kawasaki', 'Z900', 2021, 948, 'Candy Lime Green'),
('Suzuki', 'Hayabusa', 2023, 1340, 'Pearl Brilliant White'),
('Ducati', 'Monster', 2022, 937, 'Aviator Grey'),
('BMW', 'R 1250 GS', 2023, 1254, 'Triple Black'),
('Royal Enfield', 'Interceptor 650', 2021, 648, 'Raven Black'),
('Benelli', 'TNT 899', 2022, 898, 'Rosso'),
('CFMOTO', '700 CL-X', 2023, 693, 'Metallic Matte Grey'),
('Yamaha', 'Tenere 700', 2022, 689, 'Ceramic White'),
('Honda', 'CB650R', 2021, 659, 'Matte Selene Silver');