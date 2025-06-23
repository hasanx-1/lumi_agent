from langchain_core.prompts import PromptTemplate
from datetime import datetime, timedelta
from src.utils.helper import enhance_response
from src.utils.db import db_loader
from src.utils.logger import manager_logger
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
import time

class AppointmentManager:
    def __init__(self, llm=None):
        self.llm = llm
        self.slot_prompt = PromptTemplate(
            input_variables=["query", "today"],
            template="""You are a helpful assistant that extracts date and time info from user input. Today's date is {today} (e.g., Friday, 2025-04-25)
            Extract:
            - "day": either a full date (YYYY-MM-DD), or a relative word like "today", "tomorrow", or weekday like "Sunday"
            - "time": a time in HH:MM (24-hour), or natural format like "10 am", "2 pm", etc.
            Respond in this exact JSON format:
            {{"day": "...", "time": "..."}}
            Query: {query}
            """
        )
    
    def extract_day_time(self, query: str) -> dict:
        today_str = datetime.today().strftime("%A, %Y-%m-%d")
        chain = self.slot_prompt | self.llm
        result = chain.invoke({"query": query, "today": today_str})
        manager_logger.info(f"[DEBUG] Raw LLM output: {result.content.strip()}")
        try:
            manager_logger.info("Extracting time from query...")
            parsed = eval(result.content.strip())
            manager_logger.info("Extracting time done...")
            return {
                "day": self.normalize_date(parsed.get("day")),
                "time": self.normalize_time(parsed.get("time"))
            }
        except Exception as e:
            manager_logger.error(f'Failed to extract time: {e}')
            return {"day": None, "time": None}
        
    def normalize_date(self, day_str):
        try:
            parsed_date = datetime.strptime(day_str, "%Y-%m-%d")
            return parsed_date.strftime("%Y-%m-%d")
        except:
            return None

    def normalize_time(self, time_str):
        try:
            parsed_time = datetime.strptime(time_str.strip(), "%H:%M")
            return parsed_time.strftime("%H:%M")
        except:
            return None

    def check_available_slots(self, query: str):
        parsed = self.extract_day_time(query)
        day_pattern = parsed["day"]
        time_pattern = parsed["time"]

        if self._is_specific_date(day_pattern):
            return self._check_specific_date(day_pattern, time_pattern)
        else:
            return self._check_recurring_pattern(day_pattern, time_pattern)

    def _is_specific_date(self, day_str):
        try:
            datetime.strptime(day_str, "%Y-%m-%d")
            return True
        except:
            return False

    def _check_specific_date(self, target_date, target_time):
        manager_logger.info(f"[DEBUG] Checking slots for: {target_date}")
        with db_loader() as session:
            result = session.execute(
                text("""
                    SELECT time FROM appointments 
                    WHERE day = :day 
                    AND is_booked = FALSE 
                    ORDER BY time
                """),
                {"day": target_date}
            )
            slots = [r[0].strftime("%H:%M") for r in result.fetchall()]
        manager_logger.info(f"[DEBUG] Found {len(slots)} slots: {slots}")
        return [(target_date, slots)]

    def _check_recurring_pattern(self, day_pattern, target_time):
        today = datetime.today().date()
        matches = []
        for delta in range(0, 14):
            current_date = today + timedelta(days=delta)
            current_weekday = current_date.strftime("%A").lower()
            if day_pattern.lower() in current_weekday:
                date_str = current_date.strftime("%Y-%m-%d")
                with db_loader() as session:
                    result = session.execute(
                        text("""
                            SELECT time FROM appointments 
                            WHERE day = :day 
                            AND is_booked = FALSE 
                            AND time > CURRENT_TIME
                        """),
                        {"day": date_str}
                    )
                    slots = [r[0].strftime("%H:%M") for r in result.fetchall()]
                    if slots:
                        matches.append((date_str, slots))
        return matches
    
    def book_appointment(self, user_id: str, chat_id: str, day: str, time_str: str, retries=3, delay=0.5):
        for attempt in range(retries):
            try:
                with db_loader() as session:
                    # Check availability and lock row
                    result = session.execute(
                        text("""
                            SELECT appoin_id FROM appointments
                            WHERE day = :day AND time = :time AND is_booked = FALSE
                            FOR UPDATE
                        """),
                        {"day": day, "time": time_str}
                    ).fetchone()
                    if not result:
                        return f"Sorry, {time_str} on {day} is not available."

                    appoin_id = result[0]
                    # Update appointments
                    session.execute(
                        text("UPDATE appointments SET is_booked = TRUE WHERE appoin_id = :appoin_id"),
                        {"appoin_id": appoin_id}
                    )
                    # Insert reservation
                    session.execute(
                        text("""
                            INSERT INTO reservations (user_id, chat_id, appoin_id, day, time)
                            VALUES (:user_id, :chat_id, :appoin_id, :day, :time)
                        """),
                        {"user_id": user_id, "chat_id": chat_id, "appoin_id": appoin_id, "day": day, "time" : time_str}
                    )
                    session.commit()
                    resp = f"Your appointment has been booked for {day} at {time_str}!"
                    return resp
            except OperationalError as e:
                if "deadlock" in str(e).lower() and attempt < retries - 1:
                    manager_logger.warning(f"Deadlock detected, retrying {attempt + 1}/{retries}...")
                    time.sleep(delay)
                    continue
                manager_logger.error(f"Booking failed: {e}")
                return "Failed to book appointment due to database error. Please try again later."
            except Exception as e:
                manager_logger.error(f"Booking failed: {e}")
                return f"Failed to book appointment: {str(e)}"
        return "Failed to book appointment after retries. Please try again later."

    def cancel_appointment(self, user_id: str, day: str, time: str):
        with db_loader() as session:
            # Find appointment
            result = session.execute(
                text("""
                    SELECT appoin_id FROM appointments
                    WHERE day = :day AND time = :time
                """),
                {"day": day, "time": time}
            ).fetchone()
            if not result:
                resp = "No such appointment found."
                return resp

            appoin_id = result[0]
            # Check reservation
            result = session.execute(
                text("""
                    SELECT reservation_id FROM reservations
                    WHERE user_id = :user_id AND appoin_id = :appoin_id
                """),
                {"user_id": user_id, "appoin_id": appoin_id}
            ).fetchone()
            if not result:
                resp = "You don't have a reservation at that time."
                return resp

            # Delete reservation and update appointment
            session.execute(
                text("""
                    DELETE FROM reservations
                    WHERE user_id = :user_id AND appoin_id = :appoin_id
                """),
                {"user_id": user_id, "appoin_id": appoin_id}
            )
            session.execute(
                text("""
                    UPDATE appointments SET is_booked = FALSE
                    WHERE appoin_id = :appoin_id
                """),
                {"appoin_id": appoin_id}
            )
            session.commit()

        resp = f"Your appointment on {day} at {time} has been cancelled."
        return resp
    
    def get_user_reservations(self, user_id: str):
        with db_loader() as session:
            result = session.execute(
                text("""
                    SELECT a.day, a.time
                    FROM reservations r

                    JOIN appointments a ON r.appoin_id = a.appoin_id
                    WHERE r.user_id = :user_id
                    ORDER BY a.day, a.time
                """),
                {"user_id": user_id}
            )
            results = result.fetchall()

        if not results:
            resp = "You have no current reservations."
            return resp

        resp = "Your reservations:\n" + "\n".join([f"- {d} at {t.strftime('%H:%M')}" for d, t in results])
        return resp
    
    def book_appointment_wrapper(self, query: str, user_id: str, chat_id: str) -> str:
        try:
            manager_logger.info(f'Booking appointment for user {user_id}')
            parsed = self.extract_day_time(query)
            day, time = parsed["day"], parsed["time"]
            if day and time:
                return self.book_appointment(user_id, chat_id, day=day, time_str=time, retries=3, delay=0.5)
            else:
                resp = "Please provide both day and time to book an appointment."
                return resp
        except Exception as e:
            manager_logger.error(f'Failed to book appointment: {e}')
            print(f"[ERROR] booking failed: {str(e)}")
            return "Failed to book appointment. Please try again."

    def cancel_appointment_wrapper(self, query: str, user_id: str) -> str:
        parsed = self.extract_day_time(query)
        day, time = parsed["day"], parsed["time"]
        if day and time:
            return self.cancel_appointment(user_id=user_id, day=day, time=time)
        else:
            resp = "Please provide the day and time of the appointment you wish to cancel."
            return resp

    def check_available_slots_wrapper(self, query: str) -> str:
        try:
            manager_logger.info("Checking available slots...")
            results = self.check_available_slots(query)
            if not results:
                resp = "No available appointments found."
                return resp
            
            response = []
            for date_str, slots in results:
                if not slots:
                    continue
                human_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A, %b %d")
                response.append(f"Available on {human_date}:")
                response.extend([f"- {t}" for t in sorted(slots)])
            if response:
                resp = "\n".join(response)
                return resp
            else:
                resp = "No slots found."
                return resp
        except Exception as e:
            manager_logger.error(f'Failed to check slots: {e}')
            print(f"[ERROR] Slot check failed: {str(e)}")
            return "Failed to check availability. Please try again."