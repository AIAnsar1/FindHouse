import asyncio
from bot.find_house import FindHouse












async def main():
    find_house = FindHouse()
    await find_house.start_bot()
    
    
    
    

if __name__ == "__main__":
    asyncio.run(main())





























