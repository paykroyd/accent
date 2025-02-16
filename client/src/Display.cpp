#include "Display.h"
#include <GxEPD2_BW.h>
#include <GxEPD2_3C.h>
#include <SPI.h>

// ESP32 pin assignments that we verified working
const int8_t kSpiPinClk = 14;  // CLK signal
const int8_t kSpiPinMosi = 23; // DIN signal
const int8_t kSpiPinCs = 17;   // CS signal
const int8_t kSpiPinDc = 16;   // DC signal
const int8_t kSpiPinRst = 18;  // RST signal
const int8_t kSpiPinBusy = 5;  // BUSY signal
const int8_t kPowerPin = 4;    // Power control

SPIClass hspi(HSPI);
GxEPD2_3C<GxEPD2_750c_Z08, GxEPD2_750c_Z08::HEIGHT>* gx_epd_ = nullptr;

void Display::Initialize() {
    Serial.println("Initializing display");

    // Power setup
    pinMode(kPowerPin, OUTPUT);
    digitalWrite(kPowerPin, HIGH);
    delay(100);

    // Allocate display buffer
    gx_epd_ = new GxEPD2_3C<GxEPD2_750c_Z08, GxEPD2_750c_Z08::HEIGHT>(
        GxEPD2_750c_Z08(kSpiPinCs, kSpiPinDc, kSpiPinRst, kSpiPinBusy)
    );

    // Initialize SPI with our verified configuration
    hspi.begin(kSpiPinClk, -1, kSpiPinMosi, kSpiPinCs);
    gx_epd_->epd2.selectSPI(hspi, SPISettings(4000000, MSBFIRST, SPI_MODE0));
    
    gx_epd_->init(115200);
    gx_epd_->setFullWindow();
    gx_epd_->firstPage();
}

void Display::Load(const uint8_t* image_data, uint32_t size, uint32_t offset) {
    Serial.printf("Loading image data: %lu bytes\n", size);

    // For 3-color display, 4 pixels per byte (2 bits per pixel)
    const uint8_t pixels_per_byte = 4;

    for (int i = 0; i < size; ++i) {
        uint8_t input = image_data[i];
        uint16_t pixels[pixels_per_byte];
        
        // Read 4 2-bit pixels per byte
        pixels[0] = ConvertPixel(input, 0xC0, 6);
        pixels[1] = ConvertPixel(input, 0x30, 4);
        pixels[2] = ConvertPixel(input, 0x0C, 2);
        pixels[3] = ConvertPixel(input, 0x03, 0);

        // Write pixels to display
        for (int in = 0; in < pixels_per_byte; ++in) {
            uint16_t pixel = pixels[in];
            uint32_t out = pixels_per_byte * (offset + i) + in;
            int16_t x = out % gx_epd_->width();
            int16_t y = out / gx_epd_->width();
            gx_epd_->drawPixel(x, y, pixel);

            // Update display after each page
            if ((y + 1) % gx_epd_->pageHeight() == 0 && x == gx_epd_->width() - 1) {
                Serial.println("Updating display");
                gx_epd_->nextPage();
            }
        }
    }
}

void Display::Finalize() {
    Serial.println("Suspending display");
    gx_epd_->hibernate();
    delete gx_epd_;
    gx_epd_ = nullptr;
}

void Display::ShowError() {
    ShowStatic(kErrorImageBlack, kErrorImageRed, kErrorWidth, kErrorHeight, GxEPD_WHITE);
}

void Display::ShowWifiSetup() {
    ShowStatic(kWifiImageBlack, kWifiImageRed, kWifiWidth, kWifiHeight, GxEPD_WHITE);
}

int16_t Display::Width() { 
    return gx_epd_->width(); 
}

int16_t Display::Height() { 
    return gx_epd_->height(); 
}

uint16_t Display::ConvertPixel(uint8_t input, uint8_t mask, uint8_t shift) {
    uint8_t value = (input & mask) >> shift;
    
    // Convert to 3-color display values
    switch (value) {
        case 0x0:
            return GxEPD_BLACK;
        case 0x1:
            return GxEPD_WHITE;
        case 0x3:
            return GxEPD_RED;
        default:
            Serial.printf("Unknown color value: 0x%02X\n", value);
            return GxEPD_BLACK;
    }
}

void Display::ShowStatic(const uint8_t* black_data, const uint8_t* red_data,
                        uint16_t width, uint16_t height, uint16_t background) {
    Serial.println("Showing static image");
    Initialize();

    // Center the image
    int16_t x = (gx_epd_->width() - width) / 2;
    int16_t y = (gx_epd_->height() - height) / 2;

    do {
        gx_epd_->fillScreen(background);
        gx_epd_->fillRect(x, y, width, height, GxEPD_WHITE);
        gx_epd_->drawBitmap(x, y, black_data, width, height, GxEPD_BLACK);
        gx_epd_->drawBitmap(x, y, red_data, width, height, GxEPD_RED);
    } while (gx_epd_->nextPage());

    Finalize();
}