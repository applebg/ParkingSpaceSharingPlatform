'''This class is used to create a terrain on which parking lots will be created\n
code and meaning:
-1 : wall (black)
0 : space (gray)
1 : empty parking lot (green)
2 : parked parking lot (red)
3 : empty booked parking lot (yellow)
4 : parked booked parking lot (pink)
'''

import numpy as np


class Terrain():
    '''The basic terrain. This is intended to be inherited by parking_lot'''
    area = np.array([],[]) # area 是面積
    name = ""
    
    def __init__(self, name:str, rows:int, cols:int):
        '''name must be string, rows must be int, cols must be int\n
        rows and cols determine the area of terrain'''
        self.name = name
        arr = np.zeros((rows, cols))
        self.area = arr.astype(int)
    
    def check(self):
        '''check the object's status'''
        return print(f"the name of the terrain is {self.name},  the area of the terrain is {self.area.shape}")

    def receive(self, parking_lot):
        '''receive a parking lot object and then create a parking lot on the terrain'''
        anchor_point = parking_lot.anchor_point
        area = parking_lot.area
        self.area[anchor_point[0]:anchor_point[0] + area.shape[0], anchor_point[1]:anchor_point[1] + area.shape[1]] = area # put parking lot on the terrain

    def output_txt(self):
        '''Save the array as a text file'''
        np.savetxt('terrain_out.txt', self.area, fmt='%.0f', delimiter=',')

    def input_txt(self, filename:str):
        '''upload array to this program'''
        array = np.loadtxt(filename, delimiter=',')
        self.area = array

    def draw(self):
        '''draw the current layout'''
        print(self.area)