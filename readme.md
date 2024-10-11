
Status
1. "late_check_in" = [current_time] > [eta_ts]
2. "onTime_check_in" = [eta_ts] - [current_time] < 2hrs 
3. "early_check_in" =  [eta_ts] - [current_time] > 2hrs [Waiting_For_Confirm]
4. "replace_check_in" = check-in by replacement feature
5. "replace_by_____" = got replace by other truck

BizCase

Check-In
 1. Truck plan have 2 trips plan both are not yet check-in. [Q]: 2nd can update after 1st have been checked-in?
 2. Truck plan have 2 trips plan but 1st trip already checked-in. [Resolved]
 3. Truck plan which already checked-in but need to check-in again without plan update. [Admin] Can't check-in unless new plan update?
 4. Truck plan which already checked-in but need to replace by another truck.[Admin] 


Replacement

 1. Truck plan with 2 trips plan both didn't check-in but the 2nd round need replace by other. [Related_Check_In_1]
 2. The replacement truck have already check-in.[Duplicate]

Other

 1. User can't check-in due to not yet register [Q]: Should add register feature?
 2. Handle google sheet including maintenance and troubleshoot task.

Admin Feature Requirement

 1. How many checked-in truck (Count [late_check_in], [onTime_check_in], [early_check_in], [replace_check_in])
 2. How many replaced checked-in (Count [replace_check_in])
 3. How many normal checked-in (Count [late_check_in], [onTime_check_in], [early_check_in])

   Consider Real Time Dashbord on Admin Tab
   Metric:
        Total Check-In
            Late Check-In
            On Time Check-In
            Replace Check-In

Notification Feature?

