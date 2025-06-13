# ParkingSpaceSharingPlatform
**This is my graduate school project** 
This project simulates the supply and demand of parking spaces.
Optimization algorithms are implemented to help match such supply and demand.

## How to run this project
To run this project, users have to follow this instruction
  1. Install the latest version of Python
  2. cd to the folder which has all the files.
  3. In Python terminal, run `pip install -r requirments.txt` This will install all dependencies.
  4. open app.py and run it in a terminal
  5. On a browser, go to http://127.0.0.1:5000

## Project Explaination
In modern society, optimal utilization of limited space resoruces has attracted the attention of some scholars. 
It would be nice if we can make good use of limited space resources. To do this, I used optimization algorithms
to solve space allocation problems.
### Problem Scenario
 We imagine that parking lot owners want to lend their parking lots to some individuals who wish to borrow parking lots.
 Given a terrain on which there are parking lots, and given changing demand and supply of parking lots, how do 
 we allocate the supply side's parking space to the demand side's request?
### Algorithm
 This mathematics problem is known as **Bin Packing problem**, which is a kind of KnapSack problem.
 I use *First Fit* and *Best Fit* to solve this problem. For details, the readers are refered to my thesis article.

## main functionalities on the front end
1. Basic CRUD for three kinds of users: admin, borrower, and owners. Each one of them has his/her seperate view (UI which he/she can see).
2. Simple parking space map, which is represented by a matrix. In this matrix, each parking lot has a status code, and -1 means unwalkable wall,
   0 means walkable space, 1 to 4 represent parking lots of different status.
4. Faster query of parking lots of different status code.
5. Admin can choose either *First Fit* or *Best Fit* to be applied to the matching of parking lots.
6. Admin can compare the performance of *First Fit* and *Best Fit*

## Thesis article link
Here is the link to my thesis article: 
  https://1drv.ms/b/c/f3b927696ce844e7/ERhL8uYiPuVDsozWAj7vcl4B7oPh9AKLPusZE4J6xbJnUw?e=ScPdbr
In this thesis, the details of this project is documented.
:joy: 

## screenshots
### parking space matrix
![Screenshot from 2025-06-11 14-08-59](https://github.com/user-attachments/assets/92ee7777-6064-488e-b943-f3d85182c4e2)

### parking space matching results
![Screenshot from 2025-06-11 14-11-40](https://github.com/user-attachments/assets/c1e94158-5377-4bae-b620-b0b1ef973965)

### performance matrics
![Screenshot from 2025-06-11 14-13-03](https://github.com/user-attachments/assets/ad537ff7-fd18-4cb2-a957-85c34fa4f678)
