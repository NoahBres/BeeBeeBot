from beebeebot import BeeBeeBot

bot = BeeBeeBot("secret-token")

running = True

while running:
    message = bot.check_new_messages()

    if message != "":
        print(message)
        # bot.send_message(f"Your message but reversed: {message[::-1]}")

        if message == "how r u?":
            bot.send_message("I am doing good!!")
        else:
            bot.send_message(":DDD")