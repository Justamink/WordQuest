import { faker } from '@faker-js/faker';

// to run this file, make sure you have node.js installed and run: node faker.mjs


//students
console.log("STUDENTS: ")
for (let i = 0; i < 30; i ++) {
    const randomFirstName = faker.person.firstName();
    const randomLastName = faker.person.lastName();
    const randomEmail = faker.internet.email(); 
    const randomDate = faker.date.past({ years: 5 });

    console.log(`('${randomFirstName}', '${randomLastName}', '${randomEmail}', '${randomDate.toISOString().split('T')[0]}'), `)
}
console.log("")

//teachers
console.log("TEACHERS: ")
for (let i = 0; i < 30; i ++) {
    const randomFirstName = faker.person.firstName();
    const randomLastName = faker.person.lastName();
    const randomEmail = faker.internet.email(); 

    console.log(`('${randomFirstName}', '${randomLastName}', '${randomEmail}'), `)
}
console.log("")


//streaks   -- only pick the streaks with unique studentids
console.log("STREAKS: ")
for (let i = 0; i < 30; i ++) {
    const studentid = faker.number.int({ min: 1, max: 20 }) 
    const currStreak = faker.number.int({ min: 1, max: 50 }) 
    const longestStreak = faker.number.int({ min: 1, max: 50 }) 
    const lastpracticedate = faker.date.past({ years: 5 });

    console.log(`(${studentid}, ${currStreak}, ${longestStreak}, '${lastpracticedate.toISOString().split('T')[0]}'), `)
}
console.log("")


//student badge     -- only pick the student badges with unique studentid and badgeid composite pk
console.log("STUDENT BADGE")
for (let i = 0; i < 40; i ++) {
    const studentid = faker.number.int({ min: 1, max: 20 }) 
    const badgeid = faker.number.int({ min: 1, max: 10 }) 
    const earnedat = faker.date.past({ years: 5 });

    console.log(`(${studentid}, ${badgeid}, '${earnedat.toISOString().split('T')[0]}'), `)
}
console.log("")


// enrollment
console.log("ENROLLMENT")
for (let i = 0; i < 20; i ++) {
    const studentid = faker.number.int({ min: 1, max: 20 }) 
    const classid = faker.number.int({ min: 1, max: 20 }) 
    const enrollmentdate = faker.date.past({ years: 5 })
    const status = faker.helpers.arrayElement(['active', 'inactive'])

    console.log(`(${studentid}, ${classid}, '${enrollmentdate.toISOString().split('T')[0]}', '${status}'), `)
}
console.log("")


//practice unit
console.log("PRACTICE UNIT")
for (let i = 0; i < 20; i ++) {
    const topicid = faker.number.int({ min: 1, max: 20 }) 
    const difficulty = faker.helpers.arrayElement(['very easy', 'easy', 'medium', 'hard', 'very hard'])
    const ispublished = faker.helpers.arrayElement(['TRUE', 'FALSE'])
    const isunlockable = faker.helpers.arrayElement(['TRUE', 'FALSE'])
    const unlockrequirement = faker.number.int({ min: 1, max: 20 }) 

    console.log(`(${topicid}, '', '', '${difficulty}', ${ispublished}, ${isunlockable}, ${unlockrequirement}), `)
}
console.log("")


//class section
console.log("CLASS SECTION")
for (let i = 0; i < 20; i ++) {
    const crn = faker.number.int({ min: 293749, max: 692395 }) 
    const coursecode = faker.helpers.arrayElement(['ENGL 1001', 'ENGL 1002', 'ENGL 2001','ENGL 2002','ENGL 3001','ENGL 3002','ENGL 4001','ENGL 4002','ENGL 5001','ENGL 5002'])
    const sectionnumber = faker.number.int({ min: 200, max: 2000 }) 
    const semester = faker.helpers.arrayElement(['Fall', 'Spring', 'Summer 1', 'Summer 2', 'Winter'])
    const year = faker.number.int({ min: 2010, max: 2025 }) 
    const teacherid = faker.number.int({ min: 1, max: 20 }) 

    console.log(`(${crn}, '${coursecode}', ${sectionnumber}, '${semester}', ${year}, ${teacherid}), `)
}
console.log("")


// student progress:
console.log("STUDENT PROGRESS")
for (let i = 0; i < 20; i ++) {
    const studentid = faker.number.int({ min: 1, max: 20 }) 
    const exerciseid = faker.number.int({ min: 1, max: 20 }) 
    const iscorrect = faker.helpers.arrayElement(['TRUE', 'FALSE'])
    const attempt_number = faker.number.int({ min: 1, max: 10 }) 
    const answeredat = faker.date.past({ years: 5 });

    console.log(`(${studentid}, ${exerciseid}, '', ${iscorrect}, ${attempt_number}, '${answeredat.toISOString().split('T')[0]}'), `)
}
console.log("")


//answer choice
console.log("ANSWER CHOICE")
for (let i = 0; i < 20; i ++) {
    const exerciseid = faker.number.int({ min: 1, max: 20 }) 
    const iscorrect = faker.helpers.arrayElement(['TRUE', 'FALSE'])
    const displayorder = faker.number.int({ min: 1, max: 10 }) 

    console.log(`(${exerciseid}, '', ${iscorrect}, ${displayorder}), `)
}
console.log("")


// exercise
console.log("EXERCISE")
for (let i = 0; i < 20; i ++) {
    const unitid = faker.number.int({ min: 1, max: 20 }) 
    const questiontype = faker.helpers.arrayElement(['multiple choice', 'free respnse', 'multi select', 'fill in the blank'])
    const difficulty = faker.helpers.arrayElement(['very easy', 'easy', 'medium', 'hard', 'very hard'])
    const points = faker.number.int({ min: 1, max: 100 }) 

    console.log(`(${unitid}, '', '${questiontype}', '${difficulty}', '', ${points}), `)
}
console.log("")
