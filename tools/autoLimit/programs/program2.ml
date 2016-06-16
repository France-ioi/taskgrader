(* This program is not meant to be time nor memory efficient.
It is a reference program doing computations and using memory. *)

let max_number = 60000;;

let rec is_prime_rec n d =
    if d >= n
    then true
    else ((n mod d <> 0) && (is_prime_rec n (d+1)))
;;

let rec make_prime_list_rec n =
    if n > max_number
    then []
    else
      let ip = is_prime_rec n 2 in
      begin
        if ip
        then begin
          print_int n;
          print_char ' ';
          flush_all ();
        end;
        (is_prime_rec n 2)::(make_prime_list_rec (n+1))
      end
;;
make_prime_list_rec 2;;
