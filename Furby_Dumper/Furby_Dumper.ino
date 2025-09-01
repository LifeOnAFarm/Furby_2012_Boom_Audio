/*
 * Furby Boom EEPROM Dumper
 * 
 * Wiring for Furby Boom 25LCxxx EEPROM:
 * Pin 1 (CS)   -> ESP32 GPIO 5
 * Pin 2 (MOSI) -> ESP32 GPIO 23  
 * Pin 3 (WP)   -> GND (disable write protect)
 * Pin 4 (GND)  -> GND
 * Pin 5/6 (VCC+SCK) -> 3.3V + ESP32 GPIO 18
 * Pin 7 (HOLD/NC) -> 3.3V or leave floating
 * Pin 8 (MISO) -> ESP32 GPIO 19
 * 
 */

#include <SPI.h>

#define EEPROM_CS 5       // Chip Select
#define SPI_CLOCK 4000000
#define CHUNK_SIZE 256
//#define MAX_SIZE 8388608   // Full 8MB - MX25L6405 Boom Chip
#define MAX_SIZE 4094314   // Full 4MB - MX25L3205D 2012 Chip
#define READ_CMD 0x03     //EEPROM read command

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }

  Serial.println("========================================");
  Serial.println("Furby Boom EEPROM Dumper v1.3");
  Serial.println("Target: 25LCxxx SPI Flash/EEPROM");
  Serial.println("========================================");
  
  // Initialize pins first
  pinMode(EEPROM_CS, OUTPUT);
  digitalWrite(EEPROM_CS, HIGH);
  
  delay(100);
  
  // Initialize SPI with explicit pins
  SPI.begin(18, 19, 23, 5); // SCK, MISO, MOSI, SS
  
  delay(500);
  
  Serial.print("Chip size: ");
  Serial.print(MAX_SIZE / 1024 / 1024);
  Serial.println(" MB");
  Serial.print("Chunk size: ");
  Serial.print(CHUNK_SIZE);
  Serial.println(" bytes");
  Serial.print("SPI Clock: ");
  Serial.print(SPI_CLOCK / 1000000.0, 1);
  Serial.println(" MHz");
  Serial.print("Estimated time: ");
  Serial.print((MAX_SIZE / CHUNK_SIZE * 2) / 1000 / 60.0, 1);
  Serial.println(" minutes");
  Serial.println("========================================");
  
  // Try to identify the chip first
  Serial.println("Attempting chip identification...");
  unsigned long detectedSize = identifyChip();
  
  if (detectedSize > 0) {
    Serial.print("Auto-detected chip size: ");
    Serial.print(detectedSize);
    Serial.println(" bytes");
    
    Serial.print("Using size: ");
    Serial.print(detectedSize / 1024 / 1024);
    Serial.println(" MB");
    Serial.println();
    dumpEEPROM(detectedSize);
  } else {
    // Fallback to connection test
    Serial.println("Chip ID failed, trying basic connection test...");
    byte testData[8];
    bool success = readEEPROM(0, testData, 8);
    
    if (success) {
      Serial.println("EEPROM read successful!");
      Serial.print("First 8 bytes: ");
      for (int i = 0; i < 8; i++) {
        if (testData[i] < 0x10) Serial.print("0");
        Serial.print(testData[i], HEX);
        Serial.print(" ");
      }
      Serial.println();
      Serial.println("\nUsing default size, starting dump...\n");
      dumpEEPROM(MAX_SIZE);
    } else {
      Serial.println("ERROR: Could not read from EEPROM!");
      Serial.println("Check wiring and connections.");
      while (true) {
        delay(1000);
      }
    }
  }
  
  Serial.println("\nDump completed!");
}

void dumpEEPROM(unsigned long chipSize) {
  byte buffer[CHUNK_SIZE];
  unsigned long totalChunks = (chipSize + CHUNK_SIZE - 1) / CHUNK_SIZE;

  Serial.println("# Starting binary dump");
  Serial.print("# Total chunks: ");
  Serial.println(totalChunks);
  Serial.println("# Data:");

  for (unsigned long addr = 0; addr < chipSize; addr += CHUNK_SIZE) {
    // Handle last chunk
    int currentChunkSize = min((unsigned long)CHUNK_SIZE, chipSize - addr);
    
    if (readEEPROM(addr, buffer, currentChunkSize)) {
     
      for (int i = 0; i < currentChunkSize; i++) {
        if (buffer[i] < 0x10) Serial.print("0");
        Serial.print(buffer[i], HEX);
        Serial.print(" ");
      }
      Serial.println();
    } else {
      Serial.print("# ERROR at address 0x");
      Serial.println(addr, HEX);
    }
    
    // Progress indicator every 64KB 
    if (addr % (64*1024) == 0 && addr > 0) {
      float percent = (float)addr / chipSize * 100;
      Serial.print("# Progress: ");
      Serial.print(percent, 1);
      Serial.print("% (");
      Serial.print(addr / 1024);
      Serial.print("/");
      Serial.print(chipSize / 1024);
      Serial.println(" KB)");
    }
    
  }
  
  Serial.println("# Binary dump complete");
}

unsigned long identifyChip() {
  byte jedecID[3] = {0, 0, 0};
  
  // Try JEDEC ID command (0x9F)
  digitalWrite(EEPROM_CS, LOW);
  delayMicroseconds(1);
  
  SPI.beginTransaction(SPISettings(SPI_CLOCK, MSBFIRST, SPI_MODE0));
  
  SPI.transfer(0x9F); // JEDEC ID command
  jedecID[0] = SPI.transfer(0x00); // Manufacturer
  jedecID[1] = SPI.transfer(0x00); // Device Type  
  jedecID[2] = SPI.transfer(0x00); // Capacity
  
  SPI.endTransaction();
  
  delayMicroseconds(1);
  digitalWrite(EEPROM_CS, HIGH);
  
  Serial.print("JEDEC ID: ");
  for (int i = 0; i < 3; i++) {
    Serial.print("0x");
    if (jedecID[i] < 0x10) Serial.print("0");
    Serial.print(jedecID[i], HEX);
    Serial.print(" ");
  }
  Serial.println();
  
  // Decode manufacturer
  switch (jedecID[0]) {
    case 0xBF: Serial.println("Manufacturer: Microchip/SST"); break;
    case 0x20: Serial.println("Manufacturer: Micron/Numonyx/ST"); break;
    case 0xEF: Serial.println("Manufacturer: Winbond"); break;
    case 0x1F: Serial.println("Manufacturer: Atmel"); break;
    case 0xC2: Serial.println("Manufacturer: Macronix"); break;
    case 0x01: Serial.println("Manufacturer: Spansion/Cypress"); break;
    default:
      Serial.print("Manufacturer: Unknown (0x");
      Serial.print(jedecID[0], HEX);
      Serial.println(")");
      break;
  }
  
  // Try to decode capacity - this varies by manufacturer
  unsigned long chipSize = 0;
  
  // Standard JEDEC capacity encoding (2^N bytes)
  if (jedecID[2] >= 0x10 && jedecID[2] <= 0x20) {
    chipSize = 1UL << jedecID[2];
    Serial.print("Detected capacity: ");
    Serial.print(chipSize);
    Serial.println(" bytes");
  }
  
  // Macronix specific decoding
  else if (jedecID[0] == 0xC2) {
    switch (jedecID[2]) {
      case 0x10: chipSize = 65536; Serial.println("MX25L512 (512Kbit)"); break;
      case 0x11: chipSize = 131072; Serial.println("MX25L1005 (1Mbit)"); break;
      case 0x12: chipSize = 262144; Serial.println("MX25L2005 (2Mbit)"); break;
      case 0x13: chipSize = 524288; Serial.println("MX25L4005 (4Mbit)"); break;
      case 0x14: chipSize = 1048576; Serial.println("MX25L8005 (8Mbit)"); break;
      case 0x15: chipSize = 2097152; Serial.println("MX25L1605 (16Mbit)"); break;
      case 0x16: chipSize = 4194304; Serial.println("MX25L3205 (32Mbit)"); break;
      case 0x17: chipSize = 8388608; Serial.println("MX25L6405 (64Mbit)"); break;
      case 0x18: chipSize = 16777216; Serial.println("MX25L12805 (128Mbit)"); break;
      default:
        Serial.print("Unknown Macronix chip, ID: 0x");
        Serial.println(jedecID[2], HEX);
        break;
    }
  }
  
  // If all bytes are 0x00 or 0xFF, chip might not support JEDEC ID
  if ((jedecID[0] == 0x00 && jedecID[1] == 0x00 && jedecID[2] == 0x00) ||
      (jedecID[0] == 0xFF && jedecID[1] == 0xFF && jedecID[2] == 0xFF)) {
    Serial.println("Chip doesn't respond to JEDEC ID command");
    return 0;
  }
  
  return chipSize;
}

bool readEEPROM(unsigned long addr, byte* buf, int len) {
  if (!buf || len <= 0) return false;
  
  digitalWrite(EEPROM_CS, LOW);
  delayMicroseconds(1);
  
  SPI.beginTransaction(SPISettings(SPI_CLOCK, MSBFIRST, SPI_MODE0));
  
  // Send read command and address
  SPI.transfer(READ_CMD);
  SPI.transfer((addr >> 16) & 0xFF);
  SPI.transfer((addr >> 8) & 0xFF);
  SPI.transfer(addr & 0xFF);

  // Read data
  for (int i = 0; i < len; i++) {
    buf[i] = SPI.transfer(0x00);
  }

  SPI.endTransaction();
  
  delayMicroseconds(1);
  digitalWrite(EEPROM_CS, HIGH);
  
  return true;
}

void loop() {
  // Do nothing - dump runs once in setup
  delay(1000);
}