from fastf1.signalr_aio import Connection

topics = ["Heartbeat", "CarData.z", "Position.z",
          "ExtrapolatedClock", "TopThree", "RcmSeries",
          "TimingStats", "TimingAppData",
          "WeatherData", "TrackStatus", "DriverList",
          "RaceControlMessages", "SessionInfo",
          "SessionData", "LapCount", "TimingData"]


# Create debug message handler.
async def on_debug(**msg):
    print(msg)


# Create error handler
async def on_error(msg):
    print(msg)


# Create hub message handler
async def on_message(msg):
    print(msg)


if __name__ == "__main__":
    # Create connection
    connection = Connection('https://livetiming.formula1.com/signalr')

    # Register hub
    hub = connection.register_hub('Streaming')

    # Assign debug message handler. It streams unfiltered data, uncomment it to test.
    connection.received += on_debug

    # Assign error handler
    connection.error += on_error

    # Assign hub message handler
    hub.client.on('feed', on_message)

    # Send a message
    hub.server.invoke('Subscribe', topics)

    # Start the client
    connection.start()
