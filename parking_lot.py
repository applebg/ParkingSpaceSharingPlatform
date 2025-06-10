'''This file inherits terrain.py and is intended to put objects inside a terrain object. This way we can have multiple parking lots in a terrain'''
import terrain
import numpy as np

class Parking_lot(terrain.Terrain):
    anchor_point = (0, 0) # anchor point is the upper left corner of parking lot, attached to a terrain

    def __init__(self, name = "example", x=0, y=0, rows=20, cols=20):
        '''name is the parking lot name\n
        x, y are the anchor point coordinate\n
        rows, cols define the parking lot's area'''
        self.name = name
        arr = np.ones((rows, cols))
        self.area = arr.astype(int)
        self.anchor_point = (x, y)
    
    def check(self):
        '''check the object's status'''
        return print(f"the name of the parking lot is {self.name},  the area of the terrain is {self.area.shape}, the anchor point is {self.anchor_point}")
    
    def output_txt(self, filename:str):
        '''Save the array as a text file'''
        np.savetxt(filename, self.area, fmt='%.0f', delimiter=',')

    def count_frequency(self, target:int) -> str:
        '''count the frequency of a particular target number'''
        count = 0
        for row in self.area:
            for num in row:
                if num == target:
                    count += 1
        return count
    def report_coordinate(self, target:int) -> list :
        '''report the coordinates of a particular target number'''
        coordinates = []
        for i in range(len(self.area)):
            for j in range(len(self.area[i])):
                if self.area[i][j] == target:
                    coordinates.append(f"({i},{j})")
        return coordinates



if __name__ == "__main__":
    p = Parking_lot()
    p.input_txt("parking_lot_in.txt")
    li = p.report_coordinate(1)
    print(li)