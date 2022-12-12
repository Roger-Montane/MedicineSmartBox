#include <Arduino.h>
// Import libraries (BLEPeripheral depends on SPI)
#include <SPI.h>
#include <BLEPeripheral.h>


//definition of the BLEPeripheral Object
BLEPeripheral blePeripheral = BLEPeripheral();

// create service with a random generated UUID
BLEService Service = BLEService("00002902-0000-1000-8000-00805f9b34fb");

// create switch characteristic with the Notify characteristic
BLEIntCharacteristic bleCharacteristic = BLEIntCharacteristic("00002903-0000-1000-8000-00805f9b34fb", BLENotify | BLEWrite);

BLEDescriptor bleDescriptor = BLEDescriptor("2902", "CCCD");


//connect event handler
void blePeripheralConnectHandler(BLECentral& central) {
  Serial.print(F("Connected with central: "));
  Serial.println(central.address());
}

//disconnect event handler
void blePeripheralDisconnectHandler(BLECentral& central) {
  Serial.print(F("Disconnected from central: "));
  Serial.println(central.address());
}

//send data medicines
void dataSender(int codebar_medicine){
  //update value sent to central
  bleCharacteristic.setValue(codebar_medicine);

  Serial.print(F("Medicine "));
  Serial.println(codebar_medicine);
  //send information every 3 seconds
  delay(3000);
}



//setup the bluetooth service
void setup() {
  Serial.begin(9600);
#if defined (__AVR_ATmega32U4__)
  delay(5000);  //5 seconds delay for enabling to see the start up comments on the serial board
#endif

  // set advertised local name and service UUID
  blePeripheral.setLocalName("CodeBar Reader");
  blePeripheral.setAdvertisedServiceUuid(Service.uuid());

  // add service, characteristic and descriptor
  blePeripheral.addAttribute(Service);
  blePeripheral.addAttribute(bleCharacteristic);
  blePeripheral.addAttribute(bleDescriptor);

  //connect and disconnect event handlers
  blePeripheral.setEventHandler(BLEConnected, blePeripheralConnectHandler);
  blePeripheral.setEventHandler(BLEDisconnected, blePeripheralDisconnectHandler);  

  // begin initialization
  blePeripheral.begin();
}


void loop() {
  BLECentral central = blePeripheral.central();

  if (central) {
    int i;

    while (central.connected()) {
      //generate random codebars to send to the central
      do{
        i = rand() % 100000000000 + 10000;
      }while (i < 0);
      //sends data to the central
      dataSender(i);
      }
    }
  }



