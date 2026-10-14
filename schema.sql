CREATE TABLE IF NOT EXISTS public."Streak"
(
    student_id integer NOT NULL,
    current_streak integer NOT NULL,
    longest_streak integer NOT NULL,
    last_practice_day date NOT NULL,
    PRIMARY KEY (student_id)
);

CREATE TABLE IF NOT EXISTS public."StudentBadge"
(
    student_id integer NOT NULL,
    badge_id integer NOT NULL,
    earned_at date NOT NULL,
    PRIMARY KEY (student_id, badge_id)
);

CREATE TABLE IF NOT EXISTS public."Badge"
(
    badge_id SERIAL NOT NULL,
    topic_id integer,
    name text NOT NULL,
    description text NOT NULL,
    badge_type text NOT NULL,
    requirement_value integer NOT NULL,
    PRIMARY KEY (badge_id)
);

CREATE TABLE IF NOT EXISTS public."Student"
(
    student_id SERIAL NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text NOT NULL,
    created_at date NOT NULL,
    PRIMARY KEY (student_id),
    CONSTRAINT student_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS public."Teacher"
(
    teacher_id SERIAL NOT NULL,
    first_name text NOT NULL,
    last_name text NOT NULL,
    email text NOT NULL,
    PRIMARY KEY (teacher_id),
    CONSTRAINT teacher_email UNIQUE (email)
);

CREATE TABLE IF NOT EXISTS public."ClassSection"
(
    class_id SERIAL NOT NULL,
    CRN integer NOT NULL,
    course_code text NOT NULL,
    section_number integer NOT NULL,
    semester text NOT NULL,
    year integer NOT NULL,
    teacher_id integer NOT NULL,
    PRIMARY KEY (class_id)
);

CREATE TABLE IF NOT EXISTS public."Topic"
(
    topic_id SERIAL NOT NULL,
    class_id integer NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    display_order integer,
    PRIMARY KEY (topic_id)
);

CREATE TABLE IF NOT EXISTS public."Enrollment"
(
    enrollment_id SERIAL NOT NULL,
    student_id integer NOT NULL,
    class_id integer NOT NULL,
    enrollment_date date NOT NULL,
    status text NOT NULL,
    PRIMARY KEY (enrollment_id),
    CONSTRAINT student_id_class_id UNIQUE (student_id, class_id)
);

CREATE TABLE IF NOT EXISTS public."PracticeUnit"
(
    unit_id SERIAL NOT NULL,
    topic_id integer NOT NULL,
    title text NOT NULL,
    description text NOT NULL,
    difficulty text NOT NULL,
    is_published boolean NOT NULL,
    is_unlockable boolean NOT NULL,
    unlock_requirement integer,
    PRIMARY KEY (unit_id)
);

CREATE TABLE IF NOT EXISTS public."StudentProgress"
(
    progress_id SERIAL NOT NULL,
    student_id integer NOT NULL,
    exercise_id integer NOT NULL,
    submitted_answer text,
    is_correct boolean NOT NULL,
    attempt_number integer NOT NULL, 
    answered_at timestamp without time zone NOT NULL,
    PRIMARY KEY (progress_id)
);

CREATE TABLE IF NOT EXISTS public."Exercise"
(
    exercise_id SERIAL NOT NULL,
    unit_id integer NOT NULL,
    question_text text NOT NULL,
    question_type text NOT NULL,
    difficulty text NOT NULL,
    free_response_answer text,
    points integer NOT NULL,
    PRIMARY KEY (exercise_id)
);

CREATE TABLE IF NOT EXISTS public."AnswerChoice"
(
    choice_id SERIAL NOT NULL,
    exercise_id integer NOT NULL,
    choice_text text NOT NULL,
    is_correct boolean NOT NULL,
    display_order integer,
    PRIMARY KEY (choice_id)
);

CREATE TABLE IF NOT EXISTS public."Course"
(
    course_id SERIAL NOT NULL,
    course_code text NOT NULL,
    course_name text NOT NULL,
    PRIMARY KEY (course_id)
);

ALTER TABLE IF EXISTS public."Streak"
    ADD CONSTRAINT student_id FOREIGN KEY (student_id)
    REFERENCES public."Student" (student_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."StudentBadge"
    ADD CONSTRAINT student_id FOREIGN KEY (student_id)
    REFERENCES public."Student" (student_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."StudentBadge"
    ADD CONSTRAINT badge_id FOREIGN KEY (badge_id)
    REFERENCES public."Badge" (badge_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."Badge"
    ADD CONSTRAINT topic_id FOREIGN KEY (topic_id)
    REFERENCES public."Topic" (topic_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."ClassSection"
    ADD CONSTRAINT teacher_id FOREIGN KEY (teacher_id)
    REFERENCES public."Teacher" (teacher_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."Topic"
    ADD FOREIGN KEY (class_id)
    REFERENCES public."ClassSection" (class_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."Enrollment"
    ADD CONSTRAINT student_id FOREIGN KEY (student_id)
    REFERENCES public."Student" (student_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."Enrollment"
    ADD CONSTRAINT class_id FOREIGN KEY (class_id)
    REFERENCES public."ClassSection" (class_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."PracticeUnit"
    ADD CONSTRAINT topic_id FOREIGN KEY (topic_id)
    REFERENCES public."Topic" (topic_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."StudentProgress"
    ADD CONSTRAINT student_id FOREIGN KEY (student_id)
    REFERENCES public."Student" (student_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."StudentProgress"
    ADD CONSTRAINT exercise_id FOREIGN KEY (exercise_id)
    REFERENCES public."Exercise" (exercise_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."Exercise"
    ADD CONSTRAINT unit_id FOREIGN KEY (unit_id)
    REFERENCES public."PracticeUnit" (unit_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;


ALTER TABLE IF EXISTS public."AnswerChoice"
    ADD CONSTRAINT exercise_id FOREIGN KEY (exercise_id)
    REFERENCES public."Exercise" (exercise_id) MATCH SIMPLE
    ON UPDATE NO ACTION
    ON DELETE NO ACTION
    NOT VALID;