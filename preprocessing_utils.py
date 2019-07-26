import pandas as pd
from datetime import datetime as dt
import numpy as np


class preprocessing_utils:
    def __init__(self):
        pass

    def get_grib_num(self, lat, lng):
        row = (lat - self.map_bounds[0][0]) // self.grib_height
        col = (lng - self.map_bounds[0][1]) // self.grib_width
        return [int(row), int(col)]

    def get_timeslot(self, time_stamp):
        this = dt.strptime(time_stamp, self.date_format)
        slot = (this - self.start_time).total_seconds() // self.timeslot_sec
        return int(slot)

    def create_flow_matrix(self):
        return np.zeros((self.total_slot, self.map_rows, self.map_cols, 2))

    def create_trans_matrix(self):
        return np.zeros((2, self.total_slot, self.map_rows, self.map_cols, self.map_rows, self.map_cols))

    def check_lat_lng(self, lat, lng):
        if lat > self.map_bounds[0][0] or lat < self.map_bounds[1][0] or lng > self.map_bounds[1][1] or lng < \
                self.map_bounds[0][1]:
            return False
        else:
            return True

    def check_time(self, time):
        this = dt.strptime(time, self.date_format)
        if this < self.start_time or this >= self.end_time:
            return False
        else:
            return True

    def get_flow_trans_matrices_taxi(self):
        taxi1 = "data/NYTaxi/raw/yellow_tripdata_2016-01.csv"
        taxi2 = "data/NYTaxi/raw/yellow_tripdata_2016-02.csv"
        taxi3 = "data/NYTaxi/raw/yellow_tripdata_2016-03.csv"

        self.map_bounds = [[40.849878, -74.022216], [40.699031, -73.873868]]
        self.map_rows = 16
        self.map_cols = 12

        self.grib_height = (self.map_bounds[1][0] - self.map_bounds[0][0]) / self.map_rows
        self.grib_width = (self.map_bounds[1][1] - self.map_bounds[0][1]) / self.map_cols

        self.date_format = "%Y-%m-%d %H:%M:%S"

        self.day_num = 90
        self.timeslot_sec = 1800
        self.total_sec = self.day_num * 24 * 60 * 60
        self.total_slot = int(self.total_sec / self.timeslot_sec)
        self.start_time = dt.strptime("2016-01-01 00:00:00", self.date_format)
        self.end_time = dt.strptime("2016-03-31 00:00:00", self.date_format)
        self.train_size = int(int(self.day_num * 7 / 10) * 24 * 60 * 60 // self.timeslot_sec)

        flow_matrix = self.create_flow_matrix()
        trans_matrix = self.create_trans_matrix()
        trans_matrix_new = self.create_trans_matrix()
        valid_num = 0

        for idx, file in enumerate([taxi1, taxi2, taxi3]):
            print("Reading taxi file {}...".format(idx + 1))
            df = pd.read_csv(file)

            for i, row in df.iterrows():
                if i % 100000 == 0:
                    print('Taxi {} : {} rows processed, valid records: {}'.format(idx + 1, i, valid_num))

                pu_time = row['tpep_pickup_datetime']
                do_time = row['tpep_dropoff_datetime']
                pu_lat = row['pickup_latitude']
                pu_lng = row['pickup_longitude']
                do_lat = row['dropoff_latitude']
                do_lng = row['dropoff_longitude']

                if not self.check_lat_lng(pu_lat, pu_lng) or not self.check_lat_lng(do_lat, do_lng):
                    continue

                if not self.check_time(pu_time) or not self.check_time(do_time):
                    continue
                pu_slot = self.get_timeslot(pu_time)
                do_slot = self.get_timeslot(do_time)

                pu_grib = self.get_grib_num(pu_lat, pu_lng)
                do_grib = self.get_grib_num(do_lat, do_lng)
                if pu_grib == do_grib:
                    continue

                valid_num += 1
                flow_matrix[do_slot, do_grib[0], do_grib[1], 0] += 1
                flow_matrix[pu_slot, pu_grib[0], pu_grib[1], 1] += 1
                trans_matrix_new[0, do_slot, do_grib[0], do_grib[1], pu_grib[0], pu_grib[1]] += 1
                trans_matrix_new[1, pu_slot, pu_grib[0], pu_grib[1], do_grib[0], do_grib[1]] += 1
                if do_slot == pu_slot:
                    trans_matrix[0, do_slot, pu_grib[0], pu_grib[1], do_grib[0], do_grib[1]] += 1
                if do_slot - pu_slot == 1:
                    trans_matrix[1, pu_slot, pu_grib[0], pu_grib[1], do_grib[0], do_grib[1]] += 1

            print("Taxi file {} finished.".format(idx + 1))

        flow_train = flow_matrix[:self.train_size, :, :, :]
        flow_test = flow_matrix[self.train_size:, :, :, :]
        trans_train = trans_matrix[:, :self.train_size, :, :, :, :]
        trans_test = trans_matrix[:, self.train_size:, :, :, :, :]
        trans_train_new = trans_matrix_new[:, :self.train_size, :, :, :, :]
        trans_test_new = trans_matrix_new[:, self.train_size:, :, :, :, :]
        print("Total records: {}\nSaving .npz files...".format(valid_num))
        np.savez_compressed("data/NYTaxi/flow_train.npz", flow=flow_train)
        np.savez_compressed("data/NYTaxi/flow_test.npz", flow=flow_test)
        np.savez_compressed("data/NYTaxi/trans_train.npz", trans=trans_train)
        np.savez_compressed("data/NYTaxi/trans_test.npz", trans=trans_test)
        np.savez_compressed("data/NYTaxi/trans_train_new.npz", trans=trans_train_new)
        np.savez_compressed("data/NYTaxi/trans_test_new.npz", trans=trans_test_new)
        np.savez_compressed("data/NYTaxi/flow.npz", flow=flow_matrix)
        np.savez_compressed("data/NYTaxi/trans.npz", trans=trans_matrix)
        np.savez_compressed("data/NYTaxi/trans_new.npz", trans=trans_matrix_new)

    def get_flow_trans_matrices_bike(self):
        bike1 = "data/NYBike/raw/201608-citibike-tripdata.csv"
        bike2 = "data/NYBike/raw/201609-citibike-tripdata.csv"
        bike3 = "data/NYBike/raw/201610-citibike-tripdata.csv"

        self.map_bounds = [[40.818562, -74.022216], [40.699031, -73.927320]]
        self.map_rows = 14
        self.map_cols = 8

        self.grib_height = (self.map_bounds[1][0] - self.map_bounds[0][0]) / self.map_rows
        self.grib_width = (self.map_bounds[1][1] - self.map_bounds[0][1]) / self.map_cols

        self.date_format = "%m/%d/%Y %H:%M:%S"

        self.day_num = 90
        self.timeslot_sec = 1800
        self.total_sec = self.day_num * 24 * 60 * 60
        self.total_slot = int(self.total_sec / self.timeslot_sec)
        self.start_time = dt.strptime("8/1/2016 00:00:00", self.date_format)
        self.end_time = dt.strptime("10/30/2016 00:00:00", self.date_format)
        self.train_size = int(int(self.day_num * 7 / 10) * 24 * 60 * 60 // self.timeslot_sec)

        flow_matrix = self.create_flow_matrix()
        trans_matrix = self.create_trans_matrix()
        trans_matrix_new = self.create_trans_matrix()
        valid_num = 0

        for idx, file in enumerate([bike1, bike2, bike3]):
            print("Reading bike file {}...".format(idx + 1))
            df = pd.read_csv(file)
            if idx == 2:
                self.date_format = "%Y-%m-%d %H:%M:%S"

            for i, row in df.iterrows():
                if i % 100000 == 0:
                    print('Bike {} : {} rows processed, valid records: {}'.format(idx + 1, i, valid_num))

                s_time = row['starttime']
                e_time = row['stoptime']
                s_lat = row['start station latitude']
                s_lng = row['start station longitude']
                e_lat = row['end station latitude']
                e_lng = row['end station longitude']

                if not self.check_lat_lng(s_lat, s_lng) or not self.check_lat_lng(e_lat, e_lng):
                    continue

                if not self.check_time(s_time) or not self.check_time(e_time):
                    continue
                s_slot = self.get_timeslot(s_time)
                e_slot = self.get_timeslot(e_time)

                s_grib = self.get_grib_num(s_lat, s_lng)
                e_grib = self.get_grib_num(e_lat, e_lng)
                if s_grib == e_grib:
                    continue

                valid_num += 1
                flow_matrix[e_slot, e_grib[0], e_grib[1], 0] += 1
                flow_matrix[s_slot, s_grib[0], s_grib[1], 1] += 1
                trans_matrix_new[0, e_slot, e_grib[0], e_grib[1], s_grib[0], s_grib[1]] += 1
                trans_matrix_new[1, s_slot, s_grib[0], s_grib[1], e_grib[0], e_grib[1]] += 1
                if e_slot == s_slot:
                    trans_matrix[0, e_slot, s_grib[0], s_grib[1], e_grib[0], e_grib[1]] += 1
                if e_slot - s_slot == 1:
                    trans_matrix[1, s_slot, s_grib[0], s_grib[1], e_grib[0], e_grib[1]] += 1

            print("Bike file {} finished.".format(idx + 1))

        flow_train = flow_matrix[:self.train_size, :, :, :]
        flow_test = flow_matrix[self.train_size:, :, :, :]
        trans_train = trans_matrix[:, :self.train_size, :, :, :, :]
        trans_test = trans_matrix[:, self.train_size:, :, :, :, :]
        trans_train_new = trans_matrix_new[:, :self.train_size, :, :, :, :]
        trans_test_new = trans_matrix_new[:, self.train_size:, :, :, :, :]
        print("Total records: {}\nSaving .npz files...".format(valid_num))
        np.savez_compressed("data/NYBike/flow_train.npz", flow=flow_train)
        np.savez_compressed("data/NYBike/flow_test.npz", flow=flow_test)
        np.savez_compressed("data/NYBike/trans_train.npz", trans=trans_train)
        np.savez_compressed("data/NYBike/trans_test.npz", trans=trans_test)
        np.savez_compressed("data/NYBike/trans_train_new.npz", trans=trans_train_new)
        np.savez_compressed("data/NYBike/trans_test_new.npz", trans=trans_test_new)
        np.savez_compressed("data/NYBike/flow.npz", flow=flow_matrix)
        np.savez_compressed("data/NYBike/trans.npz", trans=trans_matrix)
        np.savez_compressed("data/NYBike/trans_new.npz", trans=trans_matrix_new)


if __name__ == '__main__':
    preprocessor = preprocessing_utils()
    preprocessor.get_flow_trans_matrices_bike()
    preprocessor.get_flow_trans_matrices_taxi()