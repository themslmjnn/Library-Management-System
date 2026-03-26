@router.post("/loaning_books", response_model=loan_book_schemas.LoanBookResponse, status_code=status.HTTP_201_CREATED)
def loan_book(
        db: db_dependency, 
        user: user_dependency,
        loan_book_request: loan_book_schemas.LoanBookCreate):

    return core_services.CoreService.loan_book(db, user, loan_book_request)


@router.get("/loaned_books/{user_id}", response_model=list[loan_book_schemas.LoanBookResponse], status_code=status.HTTP_200_OK)
def get_loaned_books_by_user_id(
        db: db_dependency,
        user: user_dependency,
        user_id: path_param_int_ge1):
    
    return core_services.CoreService.get_loaned_books_by_user_id(db, user, user_id)


@router.put("/users/{user_id}/returning_loans/{loan_id}", response_model=loan_book_schemas.ReturnLoanResponse, status_code=status.HTTP_200_OK)
def return_loan(
        db: db_dependency, 
        user: user_dependency,
        loan_id: path_param_int_ge1,
        user_id: path_param_int_ge1):
    
    return core_services.CoreService.return_loan(db, user, user_id, loan_id)