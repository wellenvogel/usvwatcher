from datetime import datetime
from INA219 import INA219
import threading
import time

class Values(object):
    STATUS_OK="OK"
    STATUS_NOCON="NOTCON"
    STATUS_UNDEFINED="UNDEFINED"
    def __init__(self) -> None:
        self.psuVoltage=0
        self.shuntVoltage=0
        self.loadVoltage=0
        self.current=0
        self.power=0
        self.percent=0
        self.discharging=False
        self.status=self.STATUS_UNDEFINED
        self.timestamp=time.time()
        self.dischargeStart=0


    def clone(self) -> 'Values':
        rt= Values()
        rt.__dict__=self.__dict__.copy()
        return rt

    def toPlain(self) -> dict:
        return self.__dict__.copy()

    def __str__(self) -> str:
        rt=''
        rt+="PSU Voltage:   {:6.3f} V\n".format(self.psuVoltage)
        rt+="Shunt Voltage: {:9.6f} V\n".format(self.shuntVoltage)
        rt+="Load Voltage:  {:6.3f} V\n".format(self.loadVoltage)
        rt+="Current:       {:9.6f} A\n".format(self.current)
        rt+="Power:         {:6.3f} W\n".format(self.power)
        rt+="Percent:       {:3.1f}%\n".format(self.percent)
        rt+="Discharging:   {0}\n".format(self.discharging)
        rt+="Status:        {:s}\n".format(self.status)
        rt+="Time:          {:s}\n".format(time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(self.timestamp)))
        if self.dischargeStart > 0 and self.discharging :
            rt+="DisSince:      {:s}\n".format(time.strftime("%Y/%m/%d %H:%M:%S",time.localtime(self.dischargeStart)))
        return rt


class Monitor(object):
    DISCHARGE_A=-0.2
    def __init__(self) -> None:
        self.ina=INA219(addr=0x42)
        self.currentValues=Values()
        self.lock=threading.Lock()
        self.thread=None # type: threading.Thread
        self.runCount=0;

    def queryUsv(self)->Values:
        rt=Values()
        ina=self.ina
        rt.loadVoltage=ina.getBusVoltage_V()
        rt.shuntVoltage=ina.getShuntVoltage_mV() / 1000.0
        rt.psuVoltage=rt.loadVoltage+rt.shuntVoltage
        rt.power=ina.getPower_W()
        rt.current=ina.getCurrent_mA() / 1000.0
        p = (rt.loadVoltage - 6)/2.4*100
        if(p > 100):
            p = 100
        if(p < 0):
            p = 0
        rt.percent=p
        rt.discharging=True if rt.current < self.DISCHARGE_A else False
        rt.status=rt.STATUS_OK
        return rt

    def queryRun(self) -> None:
        runCount=self.runCount
        dischargeStart=None
        while (runCount == self.runCount):
            newValues=self.queryUsv()
            if newValues.status == Values.STATUS_OK:
                if newValues.discharging:
                    if dischargeStart is None:
                        dischargeStart=time.time()
                    newValues.dischargeStart=dischargeStart
                else:
                    dischargeStart=None    

            with self.lock:
                self.currentValues=newValues
            time.sleep(2)
    def startQuery(self)->None:
        self.runCount+=1
        self.thread=threading.Thread(target=self.queryRun)
        self.thread.setDaemon(True)
        self.thread.start()
            
    def getCurrentValues(self)->Values:
        with self.lock:
            return self.currentValues.clone()


if __name__ == '__main__':
    monitor=Monitor()
    monitor.startQuery()
    values=monitor.getCurrentValues()
    last=0
    while (True):
        if values.status == Values.STATUS_OK and values.timestamp != last:
            print(values)
            last=values.timestamp
        time.sleep(0.5)
        values=monitor.getCurrentValues()


