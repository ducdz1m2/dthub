from django.core.management.base import BaseCommand
from firmware.models import FirmwareFile
import json

class Command(BaseCommand):
    help = 'Create sample firmware data'

    def handle(self, *args, **options):
        # Sample firmware data
        firmware_data = [
            {
                'name': 'ESP32 Smart Home Controller',
                'device_type': 'ESP32',
                'version': '1.0.0',
                'description': 'Firmware for ESP32-based smart home controller with WiFi connectivity and sensor support.'
            },
            {
                'name': 'ESP8266 Weather Station',
                'device_type': 'ESP8266',
                'version': '2.1.3',
                'description': 'Weather station firmware with temperature, humidity, and pressure sensors. Includes OTA update support.'
            },
            {
                'name': 'Arduino IoT Sensor Node',
                'device_type': 'Arduino',
                'version': '1.5.2',
                'description': 'Multi-sensor node firmware for Arduino with LoRa communication capabilities.'
            },
            {
                'name': 'Raspberry Pi Gateway',
                'device_type': 'Raspberry_Pi',
                'version': '3.0.1',
                'description': 'IoT gateway software for Raspberry Pi with MQTT broker and web interface.'
            }
        ]

        for data in firmware_data:
            firmware, created = FirmwareFile.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created firmware: {firmware.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Firmware already exists: {firmware.name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Sample firmware data creation completed!')
        )
